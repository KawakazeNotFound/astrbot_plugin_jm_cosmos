import asyncio

import pytest

from core.download_queue import DownloadJobQueue


@pytest.mark.asyncio
async def test_duplicate_key_is_coalesced_until_ticket_release():
    queue = DownloadJobQueue()
    first = await queue.enqueue(("umo", "user", "album", "123"))

    assert first is not None
    assert first.position == 1
    assert await queue.enqueue(("umo", "user", "album", "123")) is None

    await first.acquire()
    await first.release()

    next_job = await queue.enqueue(("umo", "user", "album", "123"))
    assert next_job is not None
    await next_job.acquire()
    await next_job.release()


@pytest.mark.asyncio
async def test_jobs_run_serially_in_fifo_order():
    queue = DownloadJobQueue()
    first = await queue.enqueue("first")
    second = await queue.enqueue("second")
    third = await queue.enqueue("third")
    assert first is not None
    assert second is not None
    assert third is not None
    assert (first.position, second.position, third.position) == (1, 2, 3)

    await first.acquire()
    started = []

    async def run(ticket, name):
        await ticket.acquire()
        try:
            started.append(name)
        finally:
            await ticket.release()

    second_task = asyncio.create_task(run(second, "second"))
    third_task = asyncio.create_task(run(third, "third"))
    await asyncio.sleep(0)
    assert started == []

    await first.release()
    await asyncio.gather(second_task, third_task)
    assert started == ["second", "third"]


@pytest.mark.asyncio
async def test_cancelled_waiter_is_removed_from_queue():
    queue = DownloadJobQueue()
    first = await queue.enqueue("first")
    second = await queue.enqueue("second")
    assert first is not None
    assert second is not None
    await first.acquire()

    async def wait_and_release(ticket):
        try:
            await ticket.acquire()
        finally:
            await ticket.release()

    waiter = asyncio.create_task(wait_and_release(second))
    await asyncio.sleep(0)
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter

    await first.release()
    replacement = await queue.enqueue("second")
    assert replacement is not None
    await replacement.acquire()
    await replacement.release()
