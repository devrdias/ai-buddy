"""Contract: the shipped hat packs follow contracts/hat-pack.md (T047)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aibuddy.hats.loader import STATES, load_hats

REPO = Path(__file__).resolve().parents[2]
SHIPPED = ["default", "geek", "coach", "sentinel"]


@pytest.fixture(scope="module")
def library():
    return load_hats(REPO / "hats")


@pytest.mark.parametrize("hat_id", SHIPPED)
def test_shipped_hat_loads_without_problems(library, hat_id):
    assert hat_id in library.hats
    assert [p for p in library.problems if p.hat_id == hat_id] == []


@pytest.mark.parametrize("hat_id", SHIPPED[1:])
def test_shipped_hat_has_a_face_for_every_state(library, hat_id):
    for state in STATES:
        assert library.face_path(library.hats[hat_id], state) is not None, (hat_id, state)


@pytest.mark.parametrize("hat_id", SHIPPED)
def test_shipped_faces_are_small_png_files(hat_id):
    for path in (REPO / "hats" / hat_id / "faces").glob("*.png"):
        data = path.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", path
        assert len(data) <= 256 * 1024, path


def test_shipped_hats_have_distinct_wording_for_the_same_event(library):
    from aibuddy.core.events import Event
    from aibuddy.core.status import frames_for_event

    event = Event.create(type="done", session_id="abc", summary="Tests passed")
    phrases = {hat_id: frames_for_event(event, hat=library.hats[hat_id])[0]["text"] for hat_id in SHIPPED[1:]}
    assert len(set(phrases.values())) == len(phrases), phrases  # SC-004: visibly different per hat
