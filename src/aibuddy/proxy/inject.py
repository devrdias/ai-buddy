"""Injection: deliver AI Buddy's own frames to every attached device (contracts/gadget-injection.md)."""

from __future__ import annotations

import asyncio


class Injector:
    def __init__(self) -> None:
        self._queues: set[asyncio.Queue] = set()
        self._latest: list[dict] = []
        self._prompt: dict | None = None

    def attach(self) -> asyncio.Queue:
        """Register a device. It receives the latest frames at once, so a reconnect shows the current state."""
        queue: asyncio.Queue = asyncio.Queue()
        for frame in self._latest:
            queue.put_nowait(frame)
        if self._prompt is not None:
            queue.put_nowait(self._prompt)
        self._queues.add(queue)
        return queue

    def detach(self, queue: asyncio.Queue) -> None:
        self._queues.discard(queue)

    def publish(self, frames: list[dict]) -> None:
        self._latest = list(frames)
        for queue in self._queues:
            for frame in frames:
                queue.put_nowait(frame)

    def publish_prompt(self, frame: dict) -> None:
        """Show an approval prompt on every device, and replay it to devices that reconnect while it is open."""
        self._prompt = frame
        for queue in self._queues:
            queue.put_nowait(frame)

    def notify(self, frames: list[dict]) -> None:
        """Send frames to every attached device without replacing the latest status or prompt."""
        for queue in self._queues:
            for frame in frames:
                queue.put_nowait(frame)

    def clear_prompt(self, frame: dict) -> None:
        """Send prompt.close to every device and forget the prompt."""
        self._prompt = None
        for queue in self._queues:
            queue.put_nowait(frame)

    @property
    def attached(self) -> int:
        return len(self._queues)
