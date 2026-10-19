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
