"""Event model: types, urgency, summary limits and redaction (data-model.md, Event)."""

from __future__ import annotations

import pytest

from aibuddy.core.events import EVENT_TYPES, URGENCY_LEVELS, Event, Session


def test_known_event_types_match_data_model():
    assert EVENT_TYPES == {
        "session_start", "working", "tool_use", "done", "error",
        "waiting", "notice", "approval_request",
    }


def test_urgency_levels_are_ordered_low_normal_urgent():
    assert URGENCY_LEVELS == ("low", "normal", "urgent")


def test_create_event_sets_id_timestamp_and_fields():
    event = Event.create(type="done", session_id="abc", summary="Tests passed")
    assert event.type == "done"
    assert event.session_id == "abc"
    assert event.urgency == "normal"
    assert event.summary == "Tests passed"
    assert event.id and event.ts > 0


def test_unknown_event_type_is_rejected():
    with pytest.raises(ValueError, match="unknown event type"):
        Event.create(type="explode", session_id="abc")


def test_unknown_urgency_is_rejected():
    with pytest.raises(ValueError, match="unknown urgency"):
        Event.create(type="done", session_id="abc", urgency="panic")


def test_summary_is_truncated_to_120_characters_with_ellipsis():
    long = "x" * 300
    event = Event.create(type="notice", session_id="abc", summary=long)
    assert len(event.summary) == 120
    assert event.summary.endswith("…")


def test_summary_defaults_to_empty_string():
    event = Event.create(type="working", session_id="abc")
    assert event.summary == ""


def test_summary_is_redacted_before_storing():
    event = Event.create(type="notice", session_id="abc",
                         summary="deploy with token ghp_abcdefghijklmnopqrstuvwxyz0123456789")
    assert "ghp_" not in event.summary
    assert "[REDACTED]" in event.summary


def test_session_tracks_last_event_and_label():
    session = Session(id="abc", label="demo")
    event = Event.create(type="working", session_id="abc")
    session.record(event)
    assert session.last_event is event
    assert session.label == "demo"
    assert session.state == "working"
