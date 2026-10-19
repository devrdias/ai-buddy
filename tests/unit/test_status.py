"""Status mapping: event types to face states, and the disconnected state (US1, FR-001/FR-002, FR-011 stale rule)."""

from __future__ import annotations

from aibuddy.core.events import Event
from aibuddy.core.status import DISCONNECTED_FRAMES, FACES, StatusTracker, face_for_event


def _event(type_: str, summary: str = "") -> Event:
    return Event.create(type=type_, session_id="abc", summary=summary)


def test_every_face_state_is_defined():
    assert FACES == {"idle", "working", "waiting", "done", "error", "disconnected"}


def test_event_types_map_to_face_states():
    assert face_for_event(_event("session_start")) == "idle"
    assert face_for_event(_event("working")) == "working"
    assert face_for_event(_event("tool_use")) == "working"
    assert face_for_event(_event("done")) == "done"
    assert face_for_event(_event("error")) == "error"
    assert face_for_event(_event("waiting")) == "waiting"
    assert face_for_event(_event("approval_request")) == "waiting"
    assert face_for_event(_event("notice")) == "idle"


def test_tracker_starts_disconnected_before_any_event():
    tracker = StatusTracker(stale_after_s=300)
    assert tracker.current_face(now=0) == "disconnected"


def test_tracker_shows_latest_event_face():
    tracker = StatusTracker(stale_after_s=300)
    tracker.record(_event("working"), now=10)
    assert tracker.current_face(now=11) == "working"
    tracker.record(_event("done"), now=20)
    assert tracker.current_face(now=21) == "done"


def test_tracker_goes_disconnected_when_events_go_stale():
    tracker = StatusTracker(stale_after_s=300)
    tracker.record(_event("working"), now=0)
    assert tracker.current_face(now=299) == "working"
    assert tracker.current_face(now=301) == "disconnected"


def test_stale_transition_is_reported_once_until_the_next_event():
    tracker = StatusTracker(stale_after_s=300)
    tracker.record(_event("working"), now=0)
    assert tracker.became_stale(now=299) is False
    assert tracker.became_stale(now=301) is True
    assert tracker.became_stale(now=400) is False  # already announced
    tracker.record(_event("done"), now=500)
    assert tracker.became_stale(now=900) is True  # a fresh stale window can be announced again


def test_disconnected_frames_show_a_clear_status_phrase():
    assert DISCONNECTED_FRAMES == [{"type": "status", "text": "Disconnected"}]
