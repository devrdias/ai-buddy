"""Remove secret-looking text before it reaches a device or the local log.

This is a safety net, not a guarantee (see the spec's privacy assumptions).
"""

from __future__ import annotations

import re

REPLACEMENT = "[REDACTED]"

# Each rule keeps any leading context (such as a header or variable name) and replaces only the secret.
_RULES = [
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), REPLACEMENT),
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), REPLACEMENT),
    (re.compile(r"AKIA[0-9A-Z]{16}"), REPLACEMENT),
    (re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"), REPLACEMENT),
    (re.compile(r"(?i)\b(Bearer)\s+[A-Za-z0-9._~+/=-]+"), rf"\1 {REPLACEMENT}"),
    (re.compile(r"(?i)\b([A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|API_?KEY|PASSWD)[A-Z0-9_]*)=\S+"),
     rf"\1={REPLACEMENT}"),
    # Command-line flags such as "--password hunter2".
    (re.compile(r"(?i)(--?(?:password|passwd|secret|token|api-?key)\s+)\S+"), rf"\1{REPLACEMENT}"),
]


def redact(text: str) -> str:
    """Return ``text`` with secret-looking substrings replaced."""
    for pattern, template in _RULES:
        text = pattern.sub(template, text)
    return text
