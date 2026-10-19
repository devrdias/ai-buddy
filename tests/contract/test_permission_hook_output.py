"""Contract: what aibuddy-hook prints for PermissionRequest (T037, contracts/hook-bridge.md).

Only an explicit approve prints allow; only an explicit deny prints deny; every other path prints nothing
and exits 0, so Claude Code shows its normal prompt. The hook never returns updatedInput or updatedPermissions.
"""

from __future__ import annotations

import io
import json

import pytest

from aibuddy.bridge.hook_cli import main

PERMISSION = {"hook_event_name": "PermissionRequest", "session_id": "abc", "cwd": "/tmp/demo",
              "tool_name": "Bash", "tool_input": {"command": "npm test"}}


class _Response:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def close(self):
        pass


def _run(monkeypatch, tmp_path, *, reply=None, error=None, capsys):
    token = tmp_path / "token"
    token.write_text("t0k3n")
    token.chmod(0o600)

    def fake_urlopen(request, timeout=None):
        if error is not None:
            raise error
        return _Response(reply)

    monkeypatch.setattr("aibuddy.bridge.hook_cli.urllib.request.urlopen", fake_urlopen)
    code = main([], stdin=io.StringIO(json.dumps(PERMISSION)), env={"AIBUDDY_TOKEN_FILE": str(token)})
    return code, capsys.readouterr().out


ALLOW = {"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior": "allow"}}}


def test_approved_prints_allow_only(monkeypatch, tmp_path, capsys):
    code, out = _run(monkeypatch, tmp_path, reply=b'{"outcome":"approved","reason":""}', capsys=capsys)
    assert code == 0
    assert json.loads(out) == ALLOW


def test_denied_prints_deny_with_message(monkeypatch, tmp_path, capsys):
    code, out = _run(monkeypatch, tmp_path, reply=b'{"outcome":"denied","reason":""}', capsys=capsys)
    decision = json.loads(out)["hookSpecificOutput"]["decision"]
    assert code == 0
    assert decision["behavior"] == "deny"
    assert decision["message"]


@pytest.mark.parametrize("reply", [
    b'{"outcome":"deferred","reason":"timeout"}',
    b'{"outcome":"approved"',  # malformed JSON
    b'{"outcome":"maybe"}',    # unknown outcome
    b'[]',
])
def test_deferred_or_unclear_replies_print_nothing(monkeypatch, tmp_path, capsys, reply):
    code, out = _run(monkeypatch, tmp_path, reply=reply, capsys=capsys)
    assert code == 0
    assert out == ""


def test_unreachable_buddy_prints_nothing(monkeypatch, tmp_path, capsys):
    code, out = _run(monkeypatch, tmp_path, error=OSError("refused"), capsys=capsys)
    assert code == 0
    assert out == ""


def test_output_never_changes_input_or_permissions(monkeypatch, tmp_path, capsys):
    _, out = _run(monkeypatch, tmp_path, reply=b'{"outcome":"approved","reason":""}', capsys=capsys)
    assert "updatedInput" not in out and "updatedPermissions" not in out
