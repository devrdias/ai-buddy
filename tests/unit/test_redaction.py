"""Redaction removes secret-looking text before it can reach a device or the log."""

from __future__ import annotations

import pytest

from aibuddy.core.redaction import redact


@pytest.mark.parametrize("secret", [
    "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
    "sk-abcdefghijklmnopqrstuvwxyz012345",
    "AKIAABCDEFGHIJKLMNOP",
    "xoxb-1234567890-abcdefghijkl",
])
def test_known_token_shapes_are_redacted(secret):
    assert secret not in redact(f"using {secret} now")
    assert "[REDACTED]" in redact(f"using {secret} now")


def test_bearer_tokens_are_redacted():
    out = redact("curl -H 'Authorization: Bearer abc.def.ghi'")
    assert "abc.def.ghi" not in out
    assert "Bearer [REDACTED]" in out


def test_key_value_secrets_are_redacted_keeping_the_key_name():
    out = redact("export PASSWORD=hunter2 API_KEY=12345")
    assert "hunter2" not in out and "12345" not in out
    assert "PASSWORD=[REDACTED]" in out
    assert "API_KEY=[REDACTED]" in out


def test_ordinary_text_is_unchanged():
    text = "Ran 12 tests in 3.4s, all green"
    assert redact(text) == text


def test_empty_text_is_safe():
    assert redact("") == ""
