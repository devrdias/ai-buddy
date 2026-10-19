"""The Brain interface, its pass-through default (Hermes) and a scripted stub for tests."""

from __future__ import annotations

import pytest

from aibuddy.brain.base import Brain
from aibuddy.brain.hermes import HermesPassThrough
from aibuddy.brain.stub import StubBrain


def test_brain_is_abstract():
    with pytest.raises(TypeError):
        Brain()  # type: ignore[abstract]


def test_hermes_is_the_default_pass_through_brain():
    brain = HermesPassThrough()
    assert brain.name == "hermes"
    assert {"text", "voice"} <= brain.capabilities


def test_hermes_pass_through_returns_frames_unchanged_and_records_them():
    brain = HermesPassThrough()
    frame = {"type": "text", "id": "t3", "text": "hello"}
    assert brain.forward(frame) == frame
    assert brain.forwarded == [frame]


async def test_stub_brain_yields_scripted_replies_in_order():
    brain = StubBrain(replies=[["Hel", "lo"], ["Bye"]])
    first = [chunk async for chunk in brain.converse("hi")]
    second = [chunk async for chunk in brain.converse("bye")]
    assert first == ["Hel", "lo"]
    assert second == ["Bye"]
    assert brain.inputs == ["hi", "bye"]


async def test_stub_brain_is_silent_once_its_script_runs_out():
    brain = StubBrain(replies=[["one"]])
    [chunk async for chunk in brain.converse("a")]
    assert [chunk async for chunk in brain.converse("b")] == []


def test_stub_brain_declares_capabilities():
    assert StubBrain(replies=[]).capabilities == frozenset({"text"})
