"""Quiet hours and do-not-disturb (US5, T065): hold non-urgent speech, never hide urgent items."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .events import Event


def _minutes(hhmm: str) -> int:
    hour, minute = hhmm.split(":")
    return int(hour) * 60 + int(minute)


@dataclass
class QuietPolicy:
    start: str | None = None  # "HH:MM"; None disables quiet hours
    end: str | None = None
    do_not_disturb: bool = False
    _held: list[Event] = field(default_factory=list, repr=False)

    def is_quiet(self, *, now: float) -> bool:
        if self.do_not_disturb:
            return True
        if self.start is None or self.end is None:
            return False
        current = datetime.fromtimestamp(now)
        minute = current.hour * 60 + current.minute
        start, end = _minutes(self.start), _minutes(self.end)
        if start <= end:
            return start <= minute < end
        return minute >= start or minute < end  # the window crosses midnight

    def allows_speech(self, event: Event, *, now: float) -> bool:
        if event.urgency == "urgent":
            return True
        return not self.is_quiet(now=now)

    def hold(self, event: Event, *, now: float) -> Event:
        """Keep a non-urgent event for later. Returns it so the caller can show it visually."""
        self._held.append(event)
        return event

    def release(self, *, now: float) -> list[Event]:
        """Events held during quiet time, released once the quiet time is over."""
        if self.is_quiet(now=now):
            return []
        released, self._held = self._held, []
        return released
