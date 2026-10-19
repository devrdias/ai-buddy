"""Configuration defaults stay on loopback unless the user opts in."""

from __future__ import annotations

import pytest

from aibuddy.core.config import ConfigError, load_config


def test_defaults_are_loopback_and_local_upstream():
    config = load_config(env={})
    assert config.listen_host == "127.0.0.1"
    assert config.upstream_url == "ws://127.0.0.1:8765/gadget"
    assert config.allow_lan is False


def test_lan_listen_address_is_refused_without_opt_in():
    with pytest.raises(ConfigError, match="refusing to listen"):
        load_config(env={"AIBUDDY_LISTEN_HOST": "0.0.0.0"})


def test_lan_listen_address_allowed_with_explicit_opt_in():
    config = load_config(env={"AIBUDDY_LISTEN_HOST": "0.0.0.0", "AIBUDDY_ALLOW_LAN": "true"})
    assert config.listen_host == "0.0.0.0"


def test_environment_overrides_and_token_is_hidden_from_repr():
    config = load_config(env={"AIBUDDY_UPSTREAM_TOKEN": "s3-secret", "AIBUDDY_LISTEN_PORT": "9000"})
    assert config.upstream_token == "s3-secret"
    assert config.listen_port == 9000
    assert "s3-secret" not in repr(config)


def test_bad_port_is_rejected():
    with pytest.raises(ConfigError, match="port"):
        load_config(env={"AIBUDDY_LISTEN_PORT": "70000"})
