"""Observe Hermes traffic for voice deny (T045): a spoken refusal denies the active approval and cancels the turn."""

from __future__ import annotations

import json
from typing import Callable

from ..core.approval import ApprovalBroker

CANCEL_FRAME = json.dumps({"type": "cancel"}, separators=(",", ":"))


def transcript_observer(broker: ApprovalBroker) -> Callable[[str], list[str]]:
    def observe(text: str) -> list[str]:
        try:
            frame = json.loads(text)
        except ValueError:
            return []
        if not (isinstance(frame, dict) and frame.get("type") == "transcript"):
            return []
        if broker.voice_deny(str(frame.get("text") or "")):
            return [CANCEL_FRAME]
        return []

    return observe


VOICE_NOTICE = "Voice reply unavailable: set up speech in Hermes"
NOTICE_TTL_S = 8


class VoiceFallback:
    """Shows a one-line notice when a voice message is answered with text only (T061).

    A device voice message (audio.end) starts a check. If Hermes answers with a final reply and sends no
    speech first, the device is told once that voice is not set up. Typed messages never start a check.
    """

    def __init__(self, injector) -> None:
        self._injector = injector
        self._pending = False

    def device_frame(self, text: str) -> None:
        frame = _frame(text)
        if frame is not None and frame.get("type") == "audio.end":
            self._pending = True

    def upstream_frame(self, text: str) -> list[str]:
        frame = _frame(text)
        if frame is None or not self._pending:
            return []
        kind = frame.get("type")
        if kind == "audio.start":
            self._pending = False
        elif kind == "reply" and not frame.get("interim"):
            self._pending = False
            self._injector.notify([{"type": "notice", "text": VOICE_NOTICE, "ttl_s": NOTICE_TTL_S}])
        return []


def _frame(text: str) -> dict | None:
    try:
        frame = json.loads(text)
    except ValueError:
        return None
    return frame if isinstance(frame, dict) else None
