"""aibuddy doctor (T069): quick health checks with a reason for each failure."""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from .core.config import Config
from .hats.loader import load_hats


def probe_tcp(url: str, timeout: float = 2.0) -> bool:
    """True when something accepts TCP connections at the upstream's host and port."""
    parsed = urlparse(url)
    port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    try:
        with socket.create_connection((parsed.hostname or "127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def run_checks(config: Config, *, token_path: Path, hats_dir: Path,
               probe_upstream: Callable[[str], bool] = probe_tcp) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    listen_ok = config.allow_lan or config.listen_host in ("127.0.0.1", "localhost", "::1")
    checks.append(("listen address", listen_ok,
                   f"{config.listen_host}:{config.listen_port}" if listen_ok
                   else "set AIBUDDY_ALLOW_LAN=true to listen on the network"))

    if not token_path.exists():
        checks.append(("bridge token", False, "missing; start `aibuddy run` once to create it"))
    elif token_path.stat().st_mode & 0o077:
        checks.append(("bridge token", False, f"readable by others; run `chmod 600 {token_path}`"))
    else:
        checks.append(("bridge token", True, str(token_path)))

    reachable = probe_upstream(config.upstream_url)
    checks.append(("hermes upstream", reachable,
                   config.upstream_url if reachable else f"no answer at {config.upstream_url}"))

    library = load_hats(hats_dir)
    if library.problems:
        detail = "; ".join(f"{p.hat_id}: {p.message}" for p in library.problems)
        checks.append(("hats", False, detail))
    else:
        checks.append(("hats", True, f"{len(library.hats)} loaded from {hats_dir}"))
    return checks
