"""The Brain interface: the AI that answers, behind one swappable seam (Principle I)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator


class Brain(ABC):
    name: str
    capabilities: frozenset[str]

    @abstractmethod
    def converse(self, text: str) -> AsyncIterator[str]:
        """Yield reply text chunks for one user message."""
