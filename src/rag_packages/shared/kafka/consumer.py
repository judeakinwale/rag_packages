import asyncio
from collections.abc import Callable, Awaitable
from typing import Any
import json
import logging
import inspect
from collections import defaultdict
from pydantic import ValidationError
from aiokafka import AIOKafkaConsumer, ConsumerRecord, TopicPartition
from rag_packages.contracts.events.shared_events import BaseEvent
from rag_packages.shared.kafka.rebalancer import RebalanceListener
from rag_packages.shared.kafka.producer import KafkaProducer
from rag_packages.contracts.events.shared_events import DLQEvent

logger = logging.getLogger(__name__)

HIGH_WATERMARK = 9990
LOW_WATERMARK = 9000
QUEUE_MAXSIZE = 10000


class KafkaConsumer:
    def __init__(
        self,
        topics: list[str],
        handlers: dict[str, Callable[[dict], Awaitable[None] | None]],
        event_models: dict[str, BaseEvent],
        dlq_producer: KafkaProducer,
        bootstrap_servers: str = "kafka:9092",
        service_name: str | None = None,
        overrides: dict[str, Any] | None = None,
    ):
        valid_overrides = overrides or {}
        self._topics = topics
        self._handlers = handlers
        self._event_models = event_models

        self.partition_queues: dict[TopicPartition, asyncio.Queue[ConsumerRecord]] = (
            defaultdict(lambda: asyncio.Queue(maxsize=QUEUE_MAXSIZE))
        )
        self.partition_tasks: dict[TopicPartition, asyncio.Task] = {}
        self.paused_partitions: set[TopicPartition] = set()

        self._consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            # enable_auto_commit=False,
            group_id=service_name,
            **valid_overrides,
        )
        self._listener = RebalanceListener(
            self._consumer,
            self.partition_queues,
            self.partition_tasks,
            paused_partitions=self.paused_partitions,
            partition_worker=self.partition_worker,
        )
        self._dlq_producer = dlq_producer
        self._consume_task: asyncio.Task | None = None
        self._started = False
        self.service_name = service_name

    @property
    def consumer(self) -> AIOKafkaConsumer:
        return self._consumer

    @property
    def started(self) -> bool:
        return self._started

    async def start(self):
        if self._started:
            return self._consumer

        try:
            self._consumer.subscribe(topics=self._topics, listener=self._listener)
            await self._consumer.start()
            self._started = True

            # await self.consume() # using this will block the start method
            self._consume_task = asyncio.create_task(self.consume())

            return self._consumer

        except Exception:
            await self._consumer.stop()
            self._started = False
            raise

    async def stop(self):
        if not self._started:
            raise RuntimeError("Consumer has not been started")

        try:
            # drain queues
            for queue in self.partition_queues.values():
                # proceed if draining the queue takes too long
                try:
                    await asyncio.wait_for(queue.join(), timeout=30)
                except asyncio.TimeoutError:
                    logger.warning(
                        f"[{self.service_name}] timeout while draining queues"
                    )

            # cancel current tasks
            for task in self.partition_tasks.values():
                task.cancel()

            await asyncio.gather(*self.partition_tasks.values(), return_exceptions=True)

            if self._consume_task:
                self._consume_task.cancel()
                # wait for task to finish, don't raise exception if cancelled or has other exception, return exception(s) as list instead
                await asyncio.gather(self._consume_task, return_exceptions=True)

            await self._consumer.stop()

        except Exception:
            logger.exception(f"[{self.service_name}] shutdown error")
            raise

        finally:
            self._started = False
            logger.info(f"[{self.service_name}] consumer shutdown complete")

    async def consume(self):
        if not self._started:
            raise RuntimeError("Consumer has not been started")

        try:
            async for msg in self._consumer:
                # # ? using aiokafka defaults
                # handler = self._handlers.get(msg.topic)
                # if handler:
                #     await handler(msg.value)

                # ? using custom partitions and backpressure
                topic_partition = TopicPartition(msg.topic, msg.partition)
                queue = self.partition_queues[topic_partition]

                await queue.put(msg)

                # try:
                #     queue.put_nowait(msg)
                # except asyncio.QueueFull as e:
                #     await self.send_to_dlq(self._dlq_producer, msg, e)

                # more relevant for auto-commit false
                self.handle_partition_backpressure(topic_partition)

        except asyncio.CancelledError:
            logger.warning(f"[{self.service_name}] consumer cancelled")

        except Exception:
            logger.exception(f"[{self.service_name}] consume handler error")

        finally:
            logger.info(f"[{self.service_name}] consumer stopping")

    async def send_to_dlq(
        self, producer: KafkaProducer, msg: ConsumerRecord, error: str
    ):
        # TODO: ensure .dlq events are sent to .parking-lot topic to prevent .dlq.dlq... topics

        dlq_topic = f"{msg.topic}.dlq"
        payload = DLQEvent(
            original_topic=msg.topic,
            partition=msg.partition,
            offset=msg.offset,
            timestamp=msg.timestamp,
            key=msg.key.decode() if msg.key else None,
            payload=msg.value,
            error=str(error),
        )

        try:
            if not producer.started:
                await producer.start()

            await producer.publish(dlq_topic, payload.model_dump())
        except Exception as e:
            logger.exception(
                f"[{self.service_name}] failed to send message to DLQ {dlq_topic}: {e}"
            )
            raise

    async def handle_message(self, msg: ConsumerRecord, retry_count: int = 3):

        for attempt in range(retry_count):
            try:
                logger.info(
                    f"[{self.service_name}] processing message from partition {msg.partition}: {msg.value} on topic: {msg.topic}"
                )

                event_model = self._event_models.get(msg.topic, None)
                event = (
                    event_model.model_validate(msg.value) if event_model else msg.value
                )

                handler = self._handlers.get(msg.topic)
                if handler:
                    result = handler(event)
                    if inspect.isawaitable(result):
                        await result
                    return
                else:
                    logger.warning(
                        f"[{self.service_name}] no handler found for topic: {msg.topic}"
                    )
                    raise ValueError(f"No handler for topic {msg.topic}")
                return

            except ValueError:
                raise

            except ValidationError as e:
                logger.error(
                    f"[{self.service_name}] invalid event payload for {msg.topic}: {e}"
                )
                await self.send_to_dlq(self._dlq_producer, msg, e)
                return

            except Exception as e:
                if attempt >= retry_count - 1:
                    logger.error(
                        f"[{self.service_name}] error processing {msg.topic} -> [DLQ]: {e}"
                    )
                    try:
                        await self.send_to_dlq(self._dlq_producer, msg, e)
                        return
                    except Exception:
                        logger.exception(
                            f"[{self.service_name}] failed to send message to DLQ after retries"
                        )
                        raise

                await asyncio.sleep(2**attempt)  # Exponential backoff

    async def partition_worker(
        self, partition: TopicPartition, queue: asyncio.Queue[ConsumerRecord]
    ):
        try:
            while True:
                msg = await queue.get()
                # partition_offset = OffsetAndMetadata(msg.offset + 1, "")

                try:
                    await self.handle_message(msg)
                    # await self._consumer.commit({partition: partition_offset})

                except Exception:
                    logger.exception(
                        f"[{self.service_name}] error in partition worker for partition {partition}"
                    )

                finally:
                    queue.task_done()
                    self.handle_partition_backpressure(partition)

        except asyncio.CancelledError:
            logger.warning(
                f"[{self.service_name}] consumer partition {partition} cancelled"
            )

        finally:
            # draining the queue is not needed since messages will be re-processed after rebalance
            # await drain_partition_queue(partition)

            self.handle_partition_backpressure(partition)

    def handle_partition_backpressure(self, partition: TopicPartition):
        # ? partition_queues is a defaultdict, so it will create a new queue if the partition doesn't exist
        queue = self.partition_queues.get(partition)
        if queue is None:
            self.paused_partitions.discard(partition)
            return

        if queue.qsize() >= HIGH_WATERMARK and partition not in self.paused_partitions:
            logger.warning(
                f"[{self.service_name}] partition {partition} queue size {queue.qsize()} exceeds high watermark {HIGH_WATERMARK}. Pausing consumption."
            )
            self._consumer.pause(partition)
            self.paused_partitions.add(partition)

        elif queue.qsize() <= LOW_WATERMARK and partition in self.paused_partitions:
            logger.info(
                f"[{self.service_name}] partition {partition} queue size {queue.qsize()} below low watermark {LOW_WATERMARK}. Resuming consumption."
            )
            self._consumer.resume(partition)
            self.paused_partitions.remove(partition)

    async def drain_partition_queue(
        self,
        partition: TopicPartition,
    ):
        queue = self.partition_queues.get(partition)
        if queue is None:
            self.paused_partitions.discard(partition)
            return

        while not queue.empty():
            msg = await queue.get()
            try:
                await self.handle_message(msg)
            except Exception as e:
                logger.error(
                    f"[{self.service_name}] error in partition worker during shutdown for partition {partition}: {e}"
                )
            finally:
                queue.task_done()

    def clear_partition_queue(self, partition: TopicPartition):
        queue = self.partition_queues.get(partition)
        if queue is None:
            return

        while not queue.empty():
            try:
                queue.get_nowait()
                queue.task_done()
            except asyncio.QueueEmpty:
                break
