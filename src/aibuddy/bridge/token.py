"""The bridge token: a random secret in a file only the user can read (contracts/hook-bridge.md)."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

DEFAULT_TOKEN_PATH = Path.home() / ".config" / "aibuddy" / "token"


def load_or_create_token(path: Path = DEFAULT_TOKEN_PATH) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(token)
    os.chmod(path, 0o600)
    return token
