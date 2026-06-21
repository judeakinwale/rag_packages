import asyncio
import logging
from aiokafka import ConsumerRebalanceListener
# from shared.kafka.utils import clear_partition_queue

logger = logging.getLogger(__name__)


# ! Update the RebalanceListener when enable_auto_commit=False
# With manual commits
#   Drain before revoke
#   Commit processed offsets
#   Then stop
class RebalanceListener(ConsumerRebalanceListener):
    def __init__(
        self,
        consumer,
        partition_queues,
        partition_tasks,
        paused_partitions,
        partition_worker,
    ):
        self.consumer = consumer
        self.partition_queues = partition_queues
        self.partition_tasks = partition_tasks
        self.paused_partitions = paused_partitions
        self.partition_worker = partition_worker

    async def on_partitions_revoked(self, revoked):
        logger.info(f"[rebalance] revoked: {revoked}")

        # await flush_offsets()

        # Stop workers for revoked partitions
        for tp in revoked:
            task = self.partition_tasks.pop(tp, None)
            if task:
                task.cancel()

                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(
                        f"[rebalance] partition worker for partition {tp} cancelled"
                    )

            # # Optional: clear queue to avoid stale processing
            # queue = self.partition_queues.get(tp)
            # clear_partition_queue(queue) if queue else None

            # release in-memory state for revoked partitions
            self.partition_queues.pop(tp, None)
            self.paused_partitions.discard(tp)

        # IMPORTANT: commit offsets before losing partitions (if auto-commit is OFF)
        # If you're using auto-commit, Kafka handles this for you

    async def on_partitions_assigned(self, assigned):
        logger.info(f"[rebalance] assigned: {assigned}")

        for tp in assigned:
            # Create queue if missing
            if tp not in self.partition_queues:
                self.partition_queues[tp] = asyncio.Queue(maxsize=10000)

            # Start worker if missing
            if tp not in self.partition_tasks:
                self.partition_tasks[tp] = asyncio.create_task(
                    self.partition_worker(tp, self.partition_queues[tp])
                )
