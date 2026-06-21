import asyncio


def clear_partition_queue(queue: asyncio.Queue | None = None) -> None:
    if queue is None:
        return

    while not queue.empty():
        try:
            queue.get_nowait()
            queue.task_done()
        except asyncio.QueueEmpty:
            break
