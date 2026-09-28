"""FIFO queue for user-triggered download jobs."""

import asyncio
from collections.abc import Hashable


class DownloadJobTicket:
    """A reserved queue position for one unique download request."""

    def __init__(
        self,
        queue: "DownloadJobQueue",
        key: Hashable,
        position: int,
        acquire_task: asyncio.Task,
    ) -> None:
        self._queue = queue
        self.key = key
        self.position = position
        self._acquire_task = acquire_task
        self._released = False

    async def acquire(self) -> None:
        """Wait until this ticket reaches the head of the FIFO queue."""
        await self._acquire_task

    async def release(self) -> None:
        """Release the queue slot and remove the deduplication key."""
        if self._released:
            return
        self._released = True

        if not self._acquire_task.done():
            self._acquire_task.cancel()

        acquired = False
        try:
            acquired = await self._acquire_task
        except asyncio.CancelledError:
            pass
        finally:
            if acquired:
                self._queue._execution_lock.release()
            await self._queue._forget(self.key)


class DownloadJobQueue:
    """Serialize download jobs and coalesce duplicate requests.

    The key is held from enqueue until release, covering both queued and active
    jobs. ``asyncio.Lock`` serves waiters fairly, preserving enqueue order.
    """

    def __init__(self) -> None:
        self._execution_lock = asyncio.Lock()
        self._state_lock = asyncio.Lock()
        self._keys: set[Hashable] = set()

    async def enqueue(self, key: Hashable) -> DownloadJobTicket | None:
        """Reserve a FIFO position, or return ``None`` for a duplicate key."""
        async with self._state_lock:
            if key in self._keys:
                return None

            self._keys.add(key)
            position = len(self._keys)
            acquire_task = asyncio.create_task(self._execution_lock.acquire())

        return DownloadJobTicket(self, key, position, acquire_task)

    async def _forget(self, key: Hashable) -> None:
        async with self._state_lock:
            self._keys.discard(key)
