"""Approval state machine and broker (Principle II, data-model.md: ApprovalRequest).

The rules are the point of this module: an agent action is approved only by an explicit touch or button press
on the device. Everything else (timeout, offline, error, voice) defers to the computer or denies.
"""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Callable

PREFIX = "bb-"
RISK_LEVELS = ("low", "high")
DEVICE_LINE_CHARS = 48
APPROVE_SOURCES = frozenset({"touch", "button"})
DENY_SOURCES = frozenset({"touch", "button", "voice"})
_DENY_PHRASES = frozenset({"no", "nope", "deny", "reject", "dont", "do not", "stop"})


@dataclass
class ApprovalRequest:
    id: str
    session_id: str
    tool_name: str
    summary: str
    risk: str
    timeout_s: float
    created: float
    state: str = "pending"
    reason: str = ""

    @classmethod
    def create(cls, *, session_id: str, tool_name: str, summary: str, risk: str = "low",
               timeout_s: float = 60.0, now: float | None = None) -> "ApprovalRequest":
        if risk not in RISK_LEVELS:
            raise ValueError(f"unknown risk: {risk!r}")
        req = cls(id=PREFIX + uuid.uuid4().hex[:10], session_id=session_id, tool_name=tool_name,
                  summary=summary, risk=risk, timeout_s=timeout_s,
                  created=time.time() if now is None else now)
        if risk == "high" or "\n" in summary or len(summary) > DEVICE_LINE_CHARS:
            req.state = "deferred"
            req.reason = "approve on computer"
        return req

    def expired(self, *, now: float) -> bool:
        return now - self.created >= self.timeout_s


def approve(req: ApprovalRequest, source: object) -> bool:
    if source not in APPROVE_SOURCES or req.state != "pending":
        return False
    req.state = "approved"
    return True


def deny(req: ApprovalRequest, source: object) -> bool:
    if source not in DENY_SOURCES or req.state != "pending":
        return False
    req.state = "denied"
    return True


def defer(req: ApprovalRequest, reason: str) -> bool:
    if req.state != "pending":
        return False
    req.state = "deferred"
    req.reason = reason
    return True


def is_deny_phrase(text: str) -> bool:
    """True when the whole utterance is a refusal. Partial matches do not count, so 'no problem' is not a deny."""
    normalized = re.sub(r"[^a-z' ]", "", text.lower()).replace("'", "").strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized in _DENY_PHRASES or normalized.replace(" ", "") in _DENY_PHRASES


class ApprovalBroker:
    """Holds pending requests, shows one at a time on the device, and resolves each one exactly once."""

    def __init__(self, *, on_prompt: Callable[[dict], None], on_close: Callable[[dict], None]) -> None:
        self._on_prompt = on_prompt
        self._on_close = on_close
        self._queue: deque[ApprovalRequest] = deque()
        self._requests: dict[str, ApprovalRequest] = {}
        self._waiters: dict[str, asyncio.Future] = {}
        self._active: ApprovalRequest | None = None

    @property
    def active_id(self) -> str | None:
        return self._active.id if self._active else None

    async def request(self, req: ApprovalRequest) -> str:
        """Wait until the request is resolved, then return its final state."""
        self._requests[req.id] = req
        if req.state != "pending":
            return req.state
        future = asyncio.get_running_loop().create_future()
        self._waiters[req.id] = future
        self._queue.append(req)
        self._activate()
        try:
            await asyncio.wait_for(future, timeout=req.timeout_s)
        except asyncio.TimeoutError:
            self.defer_prompt(req.id, "timeout")
        finally:
            self._waiters.pop(req.id, None)
        return req.state

    def answer(self, prompt_id: str, *, approve: bool, source: str) -> bool:
        """Apply a device answer to the prompt on screen. Only the active prompt can be answered."""
        req = self._requests.get(prompt_id)
        if req is None or req is not self._active:
            return False
        ok = approve_or_deny(req, approve, source)
        if ok:
            self._finish(req)
        return ok

    def defer_prompt(self, prompt_id: str, reason: str) -> bool:
        req = self._requests.get(prompt_id)
        if req is None or not defer(req, reason):
            return False
        self._finish(req)
        return True

    def voice_deny(self, text: str) -> bool:
        """A spoken refusal denies the active prompt. Voice can never approve."""
        req = self._active
        if req is None or not is_deny_phrase(text) or not deny(req, "voice"):
            return False
        self._finish(req)
        return True

    def _finish(self, req: ApprovalRequest) -> None:
        if self._active is req:
            self._active = None
            self._on_close({"type": "prompt.close", "id": req.id})
            self._activate()
        future = self._waiters.get(req.id)
        if future is not None and not future.done():
            future.set_result(None)

    def _activate(self) -> None:
        while self._active is None and self._queue:
            nxt = self._queue.popleft()
            if nxt.state != "pending":
                continue
            self._active = nxt
            self._on_prompt({"type": "prompt", "id": nxt.id, "title": nxt.tool_name,
                             "text": nxt.summary, "ttl_s": int(nxt.timeout_s)})


def approve_or_deny(req: ApprovalRequest, approve_it: bool, source: str) -> bool:
    return approve(req, source) if approve_it else deny(req, source)
