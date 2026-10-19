"""Reaction templates: only {session}, {tool} and {summary} are filled; everything else stays literal."""

from __future__ import annotations

import re

MAX_LEN = 200
_PLACEHOLDER = re.compile(r"\{(session|tool|summary)\}")


def render(template: str, *, session: str, tool: str, summary: str) -> str:
    values = {"session": session, "tool": tool, "summary": summary}
    text = _PLACEHOLDER.sub(lambda m: values[m.group(1)], template)
    return text[:MAX_LEN]
