"""Status: map events to face states and to the frames a device shows (US1)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..hats.templates import render
from .events import Event

FACES = frozenset({"idle", "working", "waiting", "done", "error", "disconnected"})
DISPLAY_TTL_S = 15

_FACE_FOR_TYPE = {
    "session_start": "idle",
    "working": "working",
    "tool_use": "working",
    "done": "done",
    "error": "error",
    "waiting": "waiting",
    "approval_request": "waiting",
    "notice": "idle",
}

# Default wording (hats replace this in US3). Each entry is (status phrase, show a card).
DISCONNECTED_FRAMES = [{"type": "status", "text": "Disconnected"}]

_WORDING = {
    "session_start": ("Ready", False),
    "working": ("Working", False),
    "tool_use": ("Working", False),
    "done": ("Done", True),
    "error": ("Error", True),
    "waiting": ("Needs you", True),
    "approval_request": ("Needs you", True),
    "notice": ("Note", True),
}


def face_for_event(event: Event) -> str:
    return _FACE_FOR_TYPE[event.type]


URGENCY_RANK = {"low": 0, "normal": 1, "urgent": 2}


def reaction_for(event: Event, hat) -> object | None:
    """The hat's first reaction that matches this event type and urgency, or None."""
    if hat is None:
        return None
    for reaction in hat.reactions:
        if reaction.when == event.type and URGENCY_RANK[event.urgency] >= URGENCY_RANK[reaction.urgency_min]:
            return reaction
    return None


def face_state_for(event: Event, hat=None) -> str:
    reaction = reaction_for(event, hat)
    if reaction is not None and reaction.face in FACES:
        return reaction.face
    return face_for_event(event)


def frames_for_event(event: Event, hat=None) -> list[dict]:
    """Frames the device should show for ``event``: a status phrase, plus a card for noteworthy events.

    With a hat, its matching reaction supplies the wording (templates are filled from the event).
    """
    phrase, show_card = _WORDING[event.type]
    reaction = reaction_for(event, hat)
    if reaction is not None and reaction.say:
        tool = event.summary.split(":", 1)[0] if ":" in event.summary else ""
        phrase = render(reaction.say, session=event.session_id, tool=tool, summary=event.summary) or phrase
    frames: list[dict] = [{"type": "status", "text": phrase}]
    if show_card:
        body = event.summary or phrase
        frames.append({"type": "display", "title": phrase, "body": body, "ttl_s": DISPLAY_TTL_S})
    return frames


@dataclass
class StatusTracker:
    """Remembers the latest event so the face can fall back to 'disconnected' when activity goes stale."""

    stale_after_s: float = 300.0
    _last: Event | None = field(default=None, repr=False)
    _last_at: float | None = field(default=None, repr=False)
    _announced: bool = field(default=False, repr=False)

    def record(self, event: Event, *, now: float) -> None:
        self._last = event
        self._last_at = now
        self._announced = False

    def _is_stale(self, *, now: float) -> bool:
        return self._last_at is None or now - self._last_at > self.stale_after_s

    def current_face(self, *, now: float) -> str:
        if self._is_stale(now=now):
            return "disconnected"
        return face_for_event(self._last)

    def became_stale(self, *, now: float) -> bool:
        """True once per stale window: the first check after activity goes quiet."""
        if self._announced or self._last is None or not self._is_stale(now=now):
            return False
        self._announced = True
        return True

    @property
    def last_event(self) -> Event | None:
        return self._last
