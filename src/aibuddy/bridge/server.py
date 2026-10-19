"""Loopback HTTP endpoint for Claude Code hooks (contracts/hook-bridge.md)."""

from __future__ import annotations

import hmac
import json
from typing import Callable

from aiohttp import web

from ..core.approval import ApprovalBroker, ApprovalRequest
from ..core.events import Event
from ..core.policy import QuietPolicy
from ..core.status import DISCONNECTED_FRAMES, StatusTracker, face_state_for, frames_for_event
from ..hats.faces import face_frames
from ..hats.loader import HatLibrary
from ..core.summary import approval_summary
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


APPROVAL_TIMEOUT_CAP_S = 120.0


def _authorized(request: web.Request, token: str) -> bool:
    supplied = request.headers.get("Authorization", "")
    return hmac.compare_digest(supplied, f"Bearer {token}")


def make_app(*, token: str, on_event: Callable[[Event], None],
             broker: ApprovalBroker | None = None) -> web.Application:
    async def post_event(request: web.Request) -> web.Response:
        if not _authorized(request, token):
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

    async def post_approval(request: web.Request) -> web.Response:
        if not _authorized(request, token):
            return web.Response(status=401)
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            return web.Response(status=400)
        if not isinstance(body, dict):
            return web.Response(status=400)
        try:
            timeout_s = min(float(body.get("timeout_s", 60)), APPROVAL_TIMEOUT_CAP_S)
        except (TypeError, ValueError):
            return web.Response(status=400)
        if timeout_s <= 0:
            return web.Response(status=400)
        tool = str(body.get("tool_name") or "tool")
        summary, risk = approval_summary(tool, body.get("tool_input"))
        req = ApprovalRequest.create(session_id=str(body.get("session_id") or "default"), tool_name=tool,
                                     summary=summary, risk=risk, timeout_s=timeout_s)
        state = await broker.request(req)
        return web.json_response({"outcome": state, "reason": req.reason})

    app = web.Application()
    app.router.add_post("/v1/event", post_event)
    if broker is not None:
        app.router.add_post("/v1/approval", post_approval)
    return app


def device_reply_handler(broker: ApprovalBroker) -> Callable[[str], bool]:
    """Consume the device's answers to AI Buddy's own prompts (ids starting bb-). Hermes prompts are not consumed."""
    def handle(text: str) -> bool:
        try:
            frame = json.loads(text)
        except ValueError:
            return False
        if not (isinstance(frame, dict) and frame.get("type") == "prompt.reply"):
            return False
        prompt_id = str(frame.get("id") or "")
        if not prompt_id.startswith("bb-"):
            return False
        answer = frame.get("answer")
        if answer == "yes":
            broker.answer(prompt_id, approve=True, source="button")
        elif answer == "no":
            broker.answer(prompt_id, approve=False, source="button")
        else:
            broker.defer_prompt(prompt_id, "malformed answer")
        return True

    return handle


def publish_event(event: Event, *, tracker: StatusTracker, injector: Injector,
                  library: HatLibrary | None = None, active: Callable[[], str] | None = None,
                  stream: int = 1, policy: QuietPolicy | None = None, now: float | None = None) -> None:
    """Record an event and push its frames to every attached device, in the active hat's voice and face.

    During quiet hours a non-urgent event is held (it is still recorded) and shown after quiet time ends.
    """
    tracker.record(event, now=event.ts)
    if policy is not None and not policy.allows_speech(event, now=event.ts if now is None else now):
        policy.hold(event, now=event.ts)
        return
    hat = library.get(active()) if library is not None and active is not None else None
    frames: list[dict | bytes] = list(frames_for_event(event, hat))
    if library is not None:
        face = library.face_path(hat or library.default, face_state_for(event, hat))
        if face is not None:
            frames += face_frames(str(face), stream)
    injector.publish(frames)


def release_held(*, tracker: StatusTracker, injector: Injector, policy: QuietPolicy,
                 now: float, library: HatLibrary | None = None, active: Callable[[], str] | None = None) -> int:
    """Show events held during quiet time, once quiet time is over. Returns how many were shown."""
    released = policy.release(now=now)
    for event in released:
        publish_event(event, tracker=tracker, injector=injector, library=library, active=active)
    return len(released)


def announce_staleness(tracker: StatusTracker, injector: Injector, *, now: float) -> bool:
    """Push the disconnected frame when activity has gone quiet. Returns True when it was pushed."""
    if not tracker.became_stale(now=now):
        return False
    injector.publish(DISCONNECTED_FRAMES)
    return True



