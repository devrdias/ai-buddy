"""Configuration with loopback-only defaults (constitution: local-first, least exposure)."""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import yaml

DEFAULT_UPSTREAM = "ws://127.0.0.1:8765/gadget"


class ConfigError(ValueError):
    """Raised when configuration is unsafe or malformed."""


@dataclass(frozen=True)
class Config:
    upstream_url: str = DEFAULT_UPSTREAM
    listen_host: str = "127.0.0.1"
    listen_port: int = 8770
    bridge_port: int = 8771
    upstream_token: str | None = field(default=None, repr=False)
    hats_dir: Path = Path("hats")
    allow_lan: bool = False

    def __post_init__(self) -> None:
        if not 0 < self.listen_port < 65536:
            raise ConfigError(f"listen port out of range: {self.listen_port}")
        if not self.allow_lan and not _is_loopback(self.listen_host):
            raise ConfigError(
                f"refusing to listen on {self.listen_host!r}; set allow_lan to expose the buddy on the network")


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


_ENV = {
    "AIBUDDY_UPSTREAM_URL": "upstream_url",
    "AIBUDDY_LISTEN_HOST": "listen_host",
    "AIBUDDY_LISTEN_PORT": "listen_port",
    "AIBUDDY_BRIDGE_PORT": "bridge_port",
    "AIBUDDY_UPSTREAM_TOKEN": "upstream_token",
    "AIBUDDY_HATS_DIR": "hats_dir",
    "AIBUDDY_ALLOW_LAN": "allow_lan",
}


def load_config(*, env: Mapping[str, str] | None = None, file: Path | None = None) -> Config:
    """Build a Config from an optional YAML file, overridden by environment variables."""
    values: dict = {}
    if file is not None and file.exists():
        loaded = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ConfigError(f"{file} must contain a mapping")
        values.update({k: v for k, v in loaded.items() if k in _ENV.values()})
    source = os.environ if env is None else env
    for var, key in _ENV.items():
        if var in source:
            values[key] = source[var]
    for key in ("listen_port", "bridge_port"):
        if key in values:
            values[key] = int(values[key])
    if "allow_lan" in values:
        values["allow_lan"] = str(values["allow_lan"]).lower() in {"1", "true", "yes", "on"}
    if "hats_dir" in values:
        values["hats_dir"] = Path(values["hats_dir"])
    return Config(**values)
