"""Voice and cancel through the relay (US4, T058-T060, T063): audio and control frames pass through unchanged."""

from __future__ import annotations

import asyncio
import json

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from aibuddy.proxy.relay import GadgetRelay
from tests.contract.test_gadget_relay import CHALLENGE, FakeUpstream, HELLO, WELCOME

AUDIO_START = {"type": "audio.start", "id": "a4", "stream": 4, "rate": 16000, "format": "pcm16", "mode": "hold"}
AUDIO_END = {"type": "audio.end", "id": "a4", "stream": 4, "duration_ms": 2100}
REPLY_AUDIO = bytes([0x01, 0x07, 0x00, 0x00]) + bytes(range(40))  # channel 1, stream 7, seq 0


async def _stack():
    hub = FakeUpstream()
    upstream = await serve(hub.handler, "127.0.0.1", 0)
    upstream_url = f"ws://127.0.0.1:{upstream.sockets[0].getsockname()[1]}/gadget"
    relay = GadgetRelay(upstream_url=upstream_url)
    server = await serve(relay.handle, "127.0.0.1", 0)
    return hub, upstream, server, f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/gadget"


async def _handshake(device):
    await device.recv()  # challenge
    await device.send(json.dumps(HELLO))
    await device.recv()  # welcome


async def test_voice_audio_frames_pass_through_in_both_directions():
    hub, upstream, server, url = await _stack()
    try:
        async with connect(url) as device:
            await _handshake(device)
            await device.send(json.dumps(AUDIO_START))
            await device.send(bytes([0x01, 0x04, 0x00, 0x00]) + bytes(range(64)))  # device mic frame
            await device.send(json.dumps(AUDIO_END))
            await asyncio.sleep(0.1)
            assert json.dumps(AUDIO_START) in hub.received
            assert bytes([0x01, 0x04, 0x00, 0x00]) + bytes(range(64)) in hub.received
            assert json.dumps(AUDIO_END) in hub.received
    finally:
        server.close()
        upstream.close()


async def test_hermes_reply_audio_reaches_the_device_unchanged():
    hub, upstream, server, url = await _stack()
    try:
        async with connect(url) as device:
            await _handshake(device)
            await asyncio.sleep(0.05)
            hub_ws = hub.connections[0]
            await hub_ws.send(json.dumps({"type": "audio.start", "stream": 7, "rate": 16000,
                                          "format": "pcm16", "turn": "t1"}))
            await hub_ws.send(REPLY_AUDIO)
            assert json.loads(await device.recv())["type"] == "audio.start"
            assert await device.recv() == REPLY_AUDIO
    finally:
        server.close()
        upstream.close()


async def test_cancel_from_the_device_is_relayed_to_hermes():
    hub, upstream, server, url = await _stack()
    try:
        async with connect(url) as device:
            await _handshake(device)
            await device.send(json.dumps({"type": "cancel"}))
            await asyncio.sleep(0.1)
            assert json.dumps({"type": "cancel"}) in hub.received
    finally:
        server.close()
        upstream.close()
