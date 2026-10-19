"""A scripted brain for tests: each call to converse() plays back the next scripted reply."""

from __future__ import annotations

from typing import AsyncIterator, Sequence

from .base import Brain


class StubBrain(Brain):
    name = "stub"
    capabilities = frozenset({"text"})

    def __init__(self, replies: Sequence[Sequence[str]]) -> None:
        self._replies = [list(chunks) for chunks in replies]
        self.inputs: list[str] = []

    async def converse(self, text: str) -> AsyncIterator[str]:
        self.inputs.append(text)
        if self._replies:
            for chunk in self._replies.pop(0):
                yield chunk
