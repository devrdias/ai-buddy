"""Text-only fallback (T061): a voice message answered with text alone shows a notice, once per turn."""

from __future__ import annotations

import json

from aibuddy.proxy.inject import Injector
from aibuddy.proxy.observe import VOICE_NOTICE, VoiceFallback


def _frames(queue):
    out = []
    while not queue.empty():
        out.append(queue.get_nowait())
    return out


def _reply(text="hi"):
    return json.dumps({"type": "reply", "turn": "t1", "text": text})


AUDIO_START = json.dumps({"type": "audio.start", "stream": 7, "rate": 16000, "format": "pcm16", "turn": "t1"})


def test_voice_message_answered_with_text_only_shows_the_notice_once():
    injector = Injector()
    queue = injector.attach()
    fallback = VoiceFallback(injector)
    fallback.device_frame(json.dumps({"type": "audio.end", "id": "a4", "stream": 4, "duration_ms": 900}))
    fallback.upstream_frame(_reply())
    fallback.upstream_frame(_reply("second part"))
    shown = _frames(queue)
    assert shown == [{"type": "notice", "text": VOICE_NOTICE, "ttl_s": 8}]


def test_reply_with_speech_suppresses_the_notice():
    injector = Injector()
    queue = injector.attach()
    fallback = VoiceFallback(injector)
    fallback.device_frame(json.dumps({"type": "audio.end", "id": "a4", "stream": 4}))
    fallback.upstream_frame(AUDIO_START)
    fallback.upstream_frame(_reply())
    assert _frames(queue) == []


def test_a_typed_message_never_triggers_the_notice():
    injector = Injector()
    queue = injector.attach()
    fallback = VoiceFallback(injector)
    fallback.device_frame(json.dumps({"type": "text", "id": "t3", "text": "hello"}))
    fallback.upstream_frame(_reply())
    assert _frames(queue) == []


def test_each_voice_turn_gets_its_own_check():
    injector = Injector()
    queue = injector.attach()
    fallback = VoiceFallback(injector)
    for _ in range(2):
        fallback.device_frame(json.dumps({"type": "audio.end", "id": "a4", "stream": 4}))
        fallback.upstream_frame(_reply())
    assert len(_frames(queue)) == 2


def test_interim_commentary_does_not_count_as_the_answer():
    injector = Injector()
    queue = injector.attach()
    fallback = VoiceFallback(injector)
    fallback.device_frame(json.dumps({"type": "audio.end", "id": "a4", "stream": 4}))
    fallback.upstream_frame(json.dumps({"type": "reply", "turn": "t1", "text": "Looking...", "interim": True}))
    assert _frames(queue) == []
    fallback.upstream_frame(_reply())
    assert len(_frames(queue)) == 1


def test_notify_sends_without_replacing_the_latest_status():
    injector = Injector()
    injector.publish([{"type": "status", "text": "Done"}])
    queue = injector.attach()
    _frames(queue)
    injector.notify([{"type": "notice", "text": "x", "ttl_s": 1}])
    assert _frames(queue) == [{"type": "notice", "text": "x", "ttl_s": 1}]
    assert injector.attach().get_nowait() == {"type": "status", "text": "Done"}
