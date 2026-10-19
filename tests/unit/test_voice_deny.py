"""Voice deny (T045): a spoken refusal denies the active prompt; voice never approves; partial phrases are ignored."""

from __future__ import annotations

import json

import pytest

from aibuddy.core.approval import ApprovalBroker, ApprovalRequest, is_deny_phrase
from aibuddy.proxy.observe import CANCEL_FRAME, transcript_observer


def _broker():
    frames: list[dict] = []
    return ApprovalBroker(on_prompt=frames.append, on_close=frames.append), frames


async def _start(broker, summary="Bash: npm test"):
    import asyncio

    req = ApprovalRequest.create(session_id="abc", tool_name="Bash", summary=summary, timeout_s=30)
    task = asyncio.create_task(broker.request(req))
    await asyncio.sleep(0)
    return req, task


@pytest.mark.parametrize("text", ["no", "No.", "nope", "deny", "reject", "don't", "Do not", "stop"])
def test_whole_utterance_refusals_are_recognised(text):
    assert is_deny_phrase(text)


@pytest.mark.parametrize("text", ["no problem", "yes", "yes please", "approve", "I said no to that", ""])
def test_partial_or_affirmative_speech_is_not_a_refusal(text):
    assert not is_deny_phrase(text)


async def test_spoken_no_denies_the_active_prompt_and_closes_it():
    broker, frames = _broker()
    req, task = await _start(broker)
    assert broker.voice_deny("No.") is True
    assert await task == "denied"
    assert frames[-1] == {"type": "prompt.close", "id": req.id}


async def test_spoken_yes_never_approves():
    broker, _ = _broker()
    req, task = await _start(broker)
    assert broker.voice_deny("yes") is False
    assert broker.active_id == req.id
    broker.answer(req.id, approve=True, source="button")
    assert await task == "approved"


async def test_voice_deny_with_nothing_pending_does_nothing():
    broker, _ = _broker()
    assert broker.voice_deny("no") is False


async def test_observer_turns_a_refusal_into_a_cancel_for_hermes():
    broker, _ = _broker()
    _, task = await _start(broker)
    observe = transcript_observer(broker)
    transcript = json.dumps({"type": "transcript", "text": "No"})
    assert observe(transcript) == [CANCEL_FRAME]
    assert await task == "denied"
    assert observe(json.dumps({"type": "reply", "text": "hi"})) == []
    assert observe("not json") == []
