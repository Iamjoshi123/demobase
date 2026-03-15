"""In-memory event broker for live demo session updates."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any


class LiveEventBroker:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, session_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            queues = list(self._queues.get(session_id, []))
        for queue in queues:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await queue.put(event)

    @asynccontextmanager
    async def subscribe(self, session_id: str) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=50)
        async with self._lock:
            self._queues[session_id].append(queue)
        try:
            yield queue
        finally:
            async with self._lock:
                if session_id in self._queues and queue in self._queues[session_id]:
                    self._queues[session_id].remove(queue)
                if session_id in self._queues and not self._queues[session_id]:
                    self._queues.pop(session_id, None)


event_broker = LiveEventBroker()
