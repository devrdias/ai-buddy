"""Injection: deliver AI Buddy's own frames to every attached device (contracts/gadget-injection.md)."""

from __future__ import annotations

import asyncio


class Injector:
    def __init__(self) -> None:
        self._queues: set[asyncio.Queue] = set()
        self._latest: list[dict] = []

    def attach(self) -> asyncio.Queue:
        """Register a device. It receives the latest frames at once, so a reconnect shows the current state."""
        queue: asyncio.Queue = asyncio.Queue()
        for frame in self._latest:
            queue.put_nowait(frame)
        self._queues.add(queue)
        return queue

    def detach(self, queue: asyncio.Queue) -> None:
        self._queues.discard(queue)

    def publish(self, frames: list[dict]) -> None:
        self._latest = list(frames)
        for queue in self._queues:
            for frame in frames:
                queue.put_nowait(frame)

    @property
    def attached(self) -> int:
        return len(self._queues)
