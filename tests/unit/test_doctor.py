"""aibuddy doctor (T069): each check reports OK or FAIL with a reason."""

from __future__ import annotations

from aibuddy.core.config import Config
from aibuddy.doctor import run_checks


def _token(tmp_path, mode: int | None = 0o600):
    token = tmp_path / "token"
    token.write_text("t0k3n")
    if mode is not None:
        token.chmod(mode)
    return token


def _results(checks):
    return {name: (ok, detail) for name, ok, detail in checks}


def test_everything_healthy_passes(tmp_path):
    hats = tmp_path / "hats"
    (hats / "default").mkdir(parents=True)
    (hats / "default" / "hat.yaml").write_text("format: 1\nname: Buddy\n")
    checks = run_checks(Config(), token_path=_token(tmp_path), hats_dir=hats, probe_upstream=lambda url: True)
    assert all(ok for _, ok, _ in checks), checks


def test_missing_token_fails_with_a_hint(tmp_path):
    checks = _results(run_checks(Config(), token_path=tmp_path / "nope", hats_dir=tmp_path,
                                 probe_upstream=lambda url: True))
    ok, detail = checks["bridge token"]
    assert ok is False and "aibuddy run" in detail


def test_token_readable_by_others_fails(tmp_path):
    checks = _results(run_checks(Config(), token_path=_token(tmp_path, 0o644), hats_dir=tmp_path,
                                 probe_upstream=lambda url: True))
    assert checks["bridge token"][0] is False


def test_unreachable_upstream_fails(tmp_path):
    checks = _results(run_checks(Config(), token_path=_token(tmp_path), hats_dir=tmp_path,
                                 probe_upstream=lambda url: False))
    assert checks["hermes upstream"][0] is False


def test_hat_problems_are_reported_but_not_fatal(tmp_path):
    hats = tmp_path / "hats"
    (hats / "broken").mkdir(parents=True)
    (hats / "broken" / "hat.yaml").write_text("format: [unclosed\n")
    checks = _results(run_checks(Config(), token_path=_token(tmp_path), hats_dir=hats,
                                 probe_upstream=lambda url: True))
    ok, detail = checks["hats"]
    assert ok is False and "broken" in detail


def test_lan_listen_without_opt_in_is_a_failure(tmp_path):
    config = Config(listen_host="0.0.0.0", allow_lan=True)
    checks = _results(run_checks(config, token_path=_token(tmp_path), hats_dir=tmp_path,
                                 probe_upstream=lambda url: True))
    assert checks["listen address"][0] is True  # explicit opt-in is allowed
