"""Loopback HTTP endpoint for Claude Code hooks (contracts/hook-bridge.md)."""

from __future__ import annotations

import hmac
from typing import Callable

from aiohttp import web

from ..core.events import Event
from ..core.status import DISCONNECTED_FRAMES, StatusTracker, frames_for_event
from ..proxy.inject import Injector

# Claude Code hook event name -> buddy event type.
HOOK_EVENT_TYPES = {
    "SessionStart": "session_start",
    "UserPromptSubmit": "working",
    "PreToolUse": "tool_use",
    "PostToolUse": "working",
    "Stop": "done",
    "Notification": "notice",
    "PermissionRequest": "waiting",
}


def make_app(*, token: str, on_event: Callable[[Event], None]) -> web.Application:
    async def post_event(request: web.Request) -> web.Response:
        expected = f"Bearer {token}"
        supplied = request.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied, expected):
            return web.Response(status=401)
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            return web.Response(status=400)
        if not isinstance(body, dict):
            return web.Response(status=400)
        event_type = HOOK_EVENT_TYPES.get(str(body.get("event", "")))
        if event_type is None:
            return web.Response(status=400)
        summary = str(body.get("summary") or "")
        event = Event.create(type=event_type, session_id=str(body.get("session_id") or "default"),
                             summary=summary)
        on_event(event)
        return web.Response(status=204)

    app = web.Application()
    app.router.add_post("/v1/event", post_event)
    return app


def publish_event(event: Event, *, tracker: StatusTracker, injector: Injector) -> None:
    """Record an event and push its frames to every attached device."""
    tracker.record(event, now=event.ts)
    injector.publish(frames_for_event(event))


def announce_staleness(tracker: StatusTracker, injector: Injector, *, now: float) -> bool:
    """Push the disconnected frame when activity has gone quiet. Returns True when it was pushed."""
    if not tracker.became_stale(now=now):
        return False
    injector.publish(DISCONNECTED_FRAMES)
    return True



