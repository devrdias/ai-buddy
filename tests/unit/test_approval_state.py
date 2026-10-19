"""Approval state machine (Principle II, data-model.md: ApprovalRequest). Written before the implementation.

Rules under test:
- pending -> approved only on an explicit touch or button approve (never voice, never timeout)
- pending -> denied on touch, button or voice deny
- pending -> deferred on timeout, offline, error, malformed answer, superseded or withdrawn
- high-risk or multi-line requests have no approve path and are deferred at once
- terminal states are final and late answers are ignored
"""

from __future__ import annotations

import pytest

from aibuddy.core.approval import ApprovalRequest, approve, defer, deny


def _pending(summary: str = "Bash: npm test", risk: str = "low", now: float = 1000.0) -> ApprovalRequest:
    return ApprovalRequest.create(session_id="abc", tool_name="Bash", summary=summary, risk=risk,
                                  timeout_s=60, now=now)


def test_new_low_risk_request_is_pending_with_bb_prefixed_id():
    req = _pending()
    assert req.state == "pending"
    assert req.id.startswith("bb-")


# T030: approve only on explicit touch or button
@pytest.mark.parametrize("source", ["touch", "button"])
def test_explicit_touch_or_button_approves(source):
    req = _pending()
    assert approve(req, source) is True
    assert req.state == "approved"


# T033: a voice transcript can never approve
@pytest.mark.parametrize("source", ["voice", "transcript", "timeout", "", None])
def test_no_other_source_can_approve(source):
    req = _pending()
    assert approve(req, source) is False
    assert req.state == "pending"


# T031: explicit deny from touch, button or voice
@pytest.mark.parametrize("source", ["touch", "button", "voice"])
def test_deny_from_touch_button_or_voice(source):
    req = _pending()
    assert deny(req, source) is True
    assert req.state == "denied"


def test_deny_from_unknown_source_is_ignored():
    req = _pending()
    assert deny(req, "timer") is False
    assert req.state == "pending"


# T032: every non-explicit path defers
@pytest.mark.parametrize("reason", ["timeout", "device offline", "proxy error", "malformed answer",
                                    "superseded", "withdrawn"])
def test_non_explicit_paths_defer(reason):
    req = _pending()
    assert defer(req, reason) is True
    assert req.state == "deferred"
    assert req.reason == reason


def test_timeout_expiry_is_detected_from_creation_time():
    req = _pending(now=1000.0)
    assert req.expired(now=1059.0) is False
    assert req.expired(now=1060.0) is True


# T034: high risk and multi-line requests have no approve path
def test_high_risk_request_is_deferred_at_once_with_no_approve_path():
    req = _pending(risk="high")
    assert req.state == "deferred"
    assert req.reason == "approve on computer"
    assert approve(req, "touch") is False


def test_multi_line_summary_is_deferred_at_once():
    req = _pending(summary="Bash: line one\nline two")
    assert req.state == "deferred"
    assert approve(req, "button") is False


def test_invalid_risk_level_is_rejected():
    with pytest.raises(ValueError, match="risk"):
        _pending(risk="extreme")


# T035: terminal states are final, late answers are ignored
def test_approved_request_ignores_later_deny_and_defer():
    req = _pending()
    approve(req, "touch")
    assert deny(req, "voice") is False
    assert defer(req, "timeout") is False
    assert req.state == "approved"


def test_denied_request_ignores_later_approve():
    req = _pending()
    deny(req, "button")
    assert approve(req, "touch") is False
    assert req.state == "denied"
