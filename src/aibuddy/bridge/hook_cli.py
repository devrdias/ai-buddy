"""``aibuddy-hook``: forwards Claude Code hook events to the local buddy.

Claude Code runs this for each hook. It must never block or break the agent, so it always exits 0 and prints
nothing on stdout. Only the approval path (US2) may print a decision.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import IO

from .token import DEFAULT_TOKEN_PATH

DEFAULT_ENDPOINT = "http://127.0.0.1:8771/v1/event"
APPROVAL_ENDPOINT = "http://127.0.0.1:8771/v1/approval"
# Claude Code's PermissionRequest hook timeout must be set above this (contracts/hook-bridge.md).
APPROVAL_TIMEOUT_S = 60.0
# The bridge redacts the whole summary, so the hook must not cut it first (a cut can hide a secret's tail).
SUMMARY_LIMIT = 2000
# The bridge is on loopback; a short timeout keeps a stopped buddy from slowing every hook.
_TIMEOUT_S = 0.5


def build_payload(data: dict) -> dict | None:
    """Map a Claude Code hook input to the bridge's /v1/event body, or None when there is nothing to send."""
    event = data.get("hook_event_name")
    if not isinstance(event, str):
        return None
    summary = ""
    if event in ("PreToolUse", "PermissionRequest"):
        tool = str(data.get("tool_name") or "tool")
        tool_input = data.get("tool_input")
        detail = ""
        if isinstance(tool_input, dict):
            detail = str(tool_input.get("command") or tool_input.get("file_path") or "")
        summary = f"{tool}: {detail}".strip()[:SUMMARY_LIMIT]
    return {
        "event": event,
        "session_id": str(data.get("session_id") or "default"),
        "cwd": str(data.get("cwd") or ""),
        "summary": summary,
    }


def _permission(data: dict, token: str, env) -> int:
    """Ask the buddy and print a decision only for an explicit approve or deny. Everything else prints nothing."""
    body = {
        "session_id": str(data.get("session_id") or "default"),
        "cwd": str(data.get("cwd") or ""),
        "tool_name": str(data.get("tool_name") or "tool"),
        "tool_input": data.get("tool_input"),
        "timeout_s": APPROVAL_TIMEOUT_S,
    }
    reply = _post(env.get("AIBUDDY_APPROVAL_ENDPOINT", APPROVAL_ENDPOINT), body, token,
                  timeout=APPROVAL_TIMEOUT_S + 10)
    outcome = reply.get("outcome") if isinstance(reply, dict) else None
    if outcome == "approved":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PermissionRequest",
                                                 "decision": {"behavior": "allow"}}}))
    elif outcome == "denied":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PermissionRequest",
                                                 "decision": {"behavior": "deny",
                                                              "message": "Denied from AI Buddy"}}}))
    return 0


def _post(endpoint: str, body: dict, token: str, *, timeout: float):
    """POST JSON to the bridge and return the parsed reply, or None on any failure."""
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
        try:
            return json.loads(response.read())
        finally:
            response.close()
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _read_private_token(path: Path) -> str | None:
    """The token, or None when the file is missing or readable by anyone but its owner."""
    try:
        if path.stat().st_mode & 0o077:
            return None
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def main(argv: list[str] | None = None, *, stdin: IO[str] | None = None, env: dict | None = None) -> int:
    env = os.environ if env is None else env
    try:
        data = json.load(stdin if stdin is not None else sys.stdin)
    except (ValueError, OSError):
        return 0
    if not isinstance(data, dict):
        return 0
    token_path = Path(env.get("AIBUDDY_TOKEN_FILE", str(DEFAULT_TOKEN_PATH)))
    token = _read_private_token(token_path)
    if token is None:
        return 0
    if data.get("hook_event_name") == "PermissionRequest":
        return _permission(data, token, env)
    payload = build_payload(data)
    if payload is None:
        return 0
    endpoint = env.get("AIBUDDY_ENDPOINT", DEFAULT_ENDPOINT)
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=_TIMEOUT_S).close()
    except (urllib.error.URLError, OSError, ValueError):
        pass  # the buddy is optional; never fail the agent
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
