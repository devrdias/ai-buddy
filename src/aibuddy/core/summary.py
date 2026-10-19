"""Build the short, redacted summary and risk level for an approval (T044)."""

from __future__ import annotations

import re
from typing import Any

from .redaction import redact

# Commands that must never get a one-tap approve on the device, even if they look short.
HIGH_RISK_PATTERNS = [
    re.compile(r"\brm\s+-[a-zA-Z]*[rf]"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bdd\s+if="),
    re.compile(r"\bgit\s+push\b.*--force"),
    re.compile(r"\bcurl\b.*\|\s*(?:sh|bash)\b"),
    re.compile(r"\bchmod\s+-R\b"),
    re.compile(r"\b(?:shutdown|reboot)\b"),
    re.compile(r">\s*/dev/"),
]


def approval_summary(tool_name: str, tool_input: Any) -> tuple[str, str]:
    """Return ``(summary, risk)``. The summary is redacted; the raw input never leaves this function."""
    detail = ""
    if isinstance(tool_input, dict):
        detail = str(tool_input.get("command") or tool_input.get("file_path") or tool_input.get("url") or "")
    summary = redact(f"{tool_name}: {detail}" if detail else tool_name)
    risk = "high" if any(pattern.search(detail) for pattern in HIGH_RISK_PATTERNS) else "low"
    return summary, risk
