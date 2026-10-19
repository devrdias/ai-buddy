"""Quiet hours and do-not-disturb (US5, T064): speech is held, urgent items are still shown."""

from __future__ import annotations

from datetime import datetime

from aibuddy.core.events import Event
from aibuddy.core.policy import QuietPolicy


def _at(hour: int, minute: int = 0) -> float:
    return datetime(2026, 10, 19, hour, minute).timestamp()


def _event(urgency: str = "normal") -> Event:
    return Event.create(type="done", session_id="abc", urgency=urgency, summary="Tests passed")


def test_outside_quiet_hours_speech_is_allowed():
    policy = QuietPolicy(start="22:00", end="07:00")
    assert policy.allows_speech(_event(), now=_at(12)) is True


def test_inside_quiet_hours_speech_is_suppressed_for_normal_events():
    policy = QuietPolicy(start="22:00", end="07:00")
    assert policy.allows_speech(_event(), now=_at(23)) is False
    assert policy.allows_speech(_event(), now=_at(3)) is False


def test_quiet_window_that_crosses_midnight_is_handled():
    policy = QuietPolicy(start="22:00", end="07:00")
    assert policy.is_quiet(now=_at(0, 30)) is True
    assert policy.is_quiet(now=_at(7, 0)) is False


def test_urgent_events_still_speak_during_quiet_hours():
    policy = QuietPolicy(start="22:00", end="07:00")
    assert policy.allows_speech(_event("urgent"), now=_at(23)) is True


def test_do_not_disturb_suppresses_everything_except_urgent():
    policy = QuietPolicy(do_not_disturb=True)
    assert policy.allows_speech(_event(), now=_at(12)) is False
    assert policy.allows_speech(_event("urgent"), now=_at(12)) is True


def test_held_items_are_released_after_quiet_hours_end():
    policy = QuietPolicy(start="22:00", end="07:00")
    held = policy.hold(_event(), now=_at(23))
    assert policy.release(now=_at(8)) == [held]
    assert policy.release(now=_at(9)) == []  # released once


def test_quiet_hours_disabled_by_default():
    assert QuietPolicy().allows_speech(_event(), now=_at(3)) is True


def test_publish_holds_non_urgent_events_during_quiet_hours_and_releases_them_later():
    from aibuddy.bridge.server import publish_event, release_held
    from aibuddy.core.status import StatusTracker
    from aibuddy.proxy.inject import Injector

    injector = Injector()
    queue = injector.attach()
    tracker = StatusTracker()
    policy = QuietPolicy(start="22:00", end="07:00")

    quiet_event = Event.create(type="done", session_id="abc", summary="Quiet one")
    publish_event(quiet_event, tracker=tracker, injector=injector, policy=policy, now=_at(23))
    assert queue.empty()  # nothing shown while quiet

    urgent = Event.create(type="waiting", session_id="abc", urgency="urgent", summary="Needs you")
    publish_event(urgent, tracker=tracker, injector=injector, policy=policy, now=_at(23))
    assert not queue.empty()  # urgent still shows

    release_held(tracker=tracker, injector=injector, policy=policy, now=_at(8))
    shown = []
    while not queue.empty():
        shown.append(queue.get_nowait())
    assert any(frame.get("body") == "Quiet one" for frame in shown if isinstance(frame, dict))
