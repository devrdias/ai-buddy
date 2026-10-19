"""The active hat: chosen by the user, read on every event so a switch takes effect at once (T052)."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ACTIVE_PATH = Path.home() / ".config" / "aibuddy" / "active_hat"


def read_active(path: Path = DEFAULT_ACTIVE_PATH) -> str:
    try:
        name = path.read_text(encoding="utf-8").strip()
    except OSError:
        return "default"
    return name or "default"


def write_active(hat_id: str, path: Path = DEFAULT_ACTIVE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(hat_id, encoding="utf-8")
    os.replace(tmp, path)
