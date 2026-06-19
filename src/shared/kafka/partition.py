import asyncio
import logging
from aiokafka import TopicPartition

logger = logging.getLogger(__name__)


async def partition_worker(
    partition: TopicPartition,
    queue: asyncio.Queue,
    handle_message,
    service_name: str = "Service",
):
    try:
        while True:
            msg = await queue.get()
            try:
                await handle_message(msg)
            except Exception as e:
                logger.error(
                    f"[{service_name}] error in partition worker for partition {partition}: {e}"
                )
            finally:
                queue.task_done()

    except asyncio.CancelledError:
        logger.warning(f"[{service_name}] consumer partition {partition} cancelled")
        pass
