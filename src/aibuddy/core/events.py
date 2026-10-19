"""Events and sessions (data-model.md: Event, Session)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from .redaction import redact

EVENT_TYPES = frozenset({
    "session_start", "working", "tool_use", "done", "error",
    "waiting", "notice", "approval_request",
})
URGENCY_LEVELS = ("low", "normal", "urgent")
SUMMARY_LIMIT = 120

# The state a session shows on the buddy after each event type.
_STATE_FOR_TYPE = {
    "session_start": "idle",
    "working": "working",
    "tool_use": "working",
    "done": "done",
    "error": "error",
    "waiting": "waiting",
    "notice": "idle",
    "approval_request": "waiting",
}


def _shorten(text: str, limit: int = SUMMARY_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


@dataclass(frozen=True)
class Event:
    id: str
    ts: float
    type: str
    session_id: str
    urgency: str
    summary: str

    @classmethod
    def create(cls, *, type: str, session_id: str, urgency: str = "normal",
               summary: str = "") -> "Event":
        if type not in EVENT_TYPES:
            raise ValueError(f"unknown event type: {type!r}")
        if urgency not in URGENCY_LEVELS:
            raise ValueError(f"unknown urgency: {urgency!r}")
        return cls(
            id=uuid.uuid4().hex[:12],
            ts=time.time(),
            type=type,
            session_id=session_id,
            urgency=urgency,
            summary=_shorten(redact(summary)),
        )


@dataclass
class Session:
    id: str
    label: str = ""
    last_event: Event | None = None
    state: str = "idle"
    events: list[Event] = field(default_factory=list)

    def record(self, event: Event) -> None:
        self.last_event = event
        self.state = _STATE_FOR_TYPE[event.type]
        self.events.append(event)
