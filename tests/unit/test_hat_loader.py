"""Hat manifest validation (T046, contracts/hat-pack.md): format version, unknown keys, faces and fallbacks."""

from __future__ import annotations

import pytest

from aibuddy.hats.loader import SUPPORTED_FORMAT, builtin_default, load_hats

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def _hat(root, folder, manifest: str, *, persona: str | None = None, faces=()):
    path = root / folder
    path.mkdir(parents=True)
    (path / "hat.yaml").write_text(manifest, encoding="utf-8")
    if persona is not None:
        (path / "persona.md").write_text(persona, encoding="utf-8")
    if faces:
        (path / "faces").mkdir()
        for state in faces:
            (path / "faces" / f"{state}.png").write_bytes(PNG)
    return path


def test_supported_format_is_version_one():
    assert SUPPORTED_FORMAT == 1


def test_valid_hat_loads_with_name_priority_persona_and_reactions(tmp_path):
    _hat(tmp_path, "geek", (
        "format: 1\nname: Geek\npriority: 50\npersona: persona.md\n"
        "reactions:\n  - when: done\n    say: \"Ship it.\"\n    face: done\n    speak: false\n"
    ), persona="You are a dry coding buddy.", faces=("done",))
    lib = load_hats(tmp_path)
    hat = lib.hats["geek"]
    assert hat.name == "Geek"
    assert hat.priority == 50
    assert hat.persona == "You are a dry coding buddy."
    assert hat.reactions[0].when == "done"
    assert hat.reactions[0].say == "Ship it."
    assert lib.problems == []


def test_unknown_keys_are_kept_out_but_reported_as_warnings(tmp_path):
    _hat(tmp_path, "geek", "format: 1\nname: Geek\nmood_ring: true\n")
    hat = load_hats(tmp_path).hats["geek"]
    assert any("mood_ring" in w for w in hat.warnings)


def test_unsupported_format_is_skipped_and_reported(tmp_path):
    _hat(tmp_path, "future", "format: 99\nname: Future\n")
    lib = load_hats(tmp_path)
    assert "future" not in lib.hats
    assert any(p.hat_id == "future" and "format" in p.message for p in lib.problems)


def test_broken_yaml_is_skipped_and_reported(tmp_path):
    _hat(tmp_path, "broken", "format: [unclosed\n")
    lib = load_hats(tmp_path)
    assert "broken" not in lib.hats
    assert any(p.hat_id == "broken" for p in lib.problems)


def test_reaction_with_unknown_trigger_is_dropped_with_warning(tmp_path):
    _hat(tmp_path, "geek", "format: 1\nreactions:\n  - when: moonrise\n    say: hi\n")
    hat = load_hats(tmp_path).hats["geek"]
    assert hat.reactions == ()
    assert any("moonrise" in w for w in hat.warnings)


def test_missing_face_falls_back_to_the_default_hat_face(tmp_path):
    _hat(tmp_path, "geek", "format: 1\nname: Geek\n", faces=("idle",))
    lib = load_hats(tmp_path)
    assert lib.face_path(lib.hats["geek"], "idle") is not None
    assert lib.face_path(lib.hats["geek"], "error") is None  # neither geek nor the default hat has one here


def test_oversized_face_image_is_refused(tmp_path):
    path = _hat(tmp_path, "geek", "format: 1\nname: Geek\n")
    (path / "faces").mkdir()
    (path / "faces" / "done.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * (256 * 1024 + 1))
    lib = load_hats(tmp_path)
    assert "done" not in lib.hats["geek"].faces
    assert any(p.hat_id == "geek" and "done" in p.message for p in lib.problems)


def test_a_problem_in_one_hat_does_not_stop_the_others(tmp_path):
    _hat(tmp_path, "broken", "format: [unclosed\n")
    _hat(tmp_path, "coach", "format: 1\nname: Coach\n")
    lib = load_hats(tmp_path)
    assert "coach" in lib.hats


def test_builtin_default_exists_even_with_no_folder(tmp_path):
    lib = load_hats(tmp_path / "does-not-exist")
    assert lib.default.id == "default"
    assert lib.default == builtin_default()


def test_default_hat_is_used_when_a_hat_is_missing(tmp_path):
    lib = load_hats(tmp_path)
    assert lib.get("nope") is lib.default
