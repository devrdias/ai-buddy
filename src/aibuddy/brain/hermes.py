"""Hermes Agent as the default brain.

The device conversation runs through the relay at protocol level, so this brain forwards frames rather than
generating replies itself. ``forwarded`` keeps what was passed through, which tests and the status view can read.
"""

from __future__ import annotations

from typing import AsyncIterator

from .base import Brain


class HermesPassThrough(Brain):
    name = "hermes"
    capabilities = frozenset({"text", "voice"})

    def __init__(self) -> None:
        self.forwarded: list[dict] = []

    def forward(self, frame: dict) -> dict:
        self.forwarded.append(frame)
        return frame

    async def converse(self, text: str) -> AsyncIterator[str]:
        raise NotImplementedError("Hermes conversation runs through the relay; use forward()")
        yield  # pragma: no cover  (makes this an async generator)
