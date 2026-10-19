"""aibuddy-hook: always exits 0, never prints a decision for status events, and builds sane payloads."""

from __future__ import annotations

import io
import json

from aibuddy.bridge.hook_cli import build_payload, main


def test_stop_event_maps_to_payload():
    payload = build_payload({"hook_event_name": "Stop", "session_id": "abc", "cwd": "/tmp/demo"})
    assert payload == {"event": "Stop", "session_id": "abc", "cwd": "/tmp/demo", "summary": ""}


def test_permission_summary_includes_tool_and_command_and_is_truncated():
    payload = build_payload({"hook_event_name": "PermissionRequest", "tool_name": "Bash",
                             "tool_input": {"command": "rm -rf " + "x" * 500}})
    assert payload["summary"].startswith("Bash: rm -rf ")
    assert len(payload["summary"]) <= 200


def test_input_without_event_name_builds_nothing():
    assert build_payload({"session_id": "abc"}) is None


def test_exit_is_zero_and_silent_when_stdin_is_garbage(capsys):
    assert main([], stdin=io.StringIO("not json"), env={}) == 0
    assert capsys.readouterr().out == ""


def test_exit_is_zero_when_no_token_file(tmp_path, capsys):
    stdin = io.StringIO(json.dumps({"hook_event_name": "Stop", "session_id": "abc"}))
    env = {"AIBUDDY_TOKEN_FILE": str(tmp_path / "missing")}
    assert main([], stdin=stdin, env=env) == 0
    assert capsys.readouterr().out == ""


def test_exit_is_zero_when_buddy_is_not_running(tmp_path, capsys):
    token = tmp_path / "token"
    token.write_text("t0k3n")
    stdin = io.StringIO(json.dumps({"hook_event_name": "Stop", "session_id": "abc"}))
    env = {"AIBUDDY_TOKEN_FILE": str(token), "AIBUDDY_ENDPOINT": "http://127.0.0.1:9/v1/event"}
    assert main([], stdin=stdin, env=env) == 0
    assert capsys.readouterr().out == ""
