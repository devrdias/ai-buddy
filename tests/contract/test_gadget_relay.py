"""Contract: the relay passes Hermes Gadget traffic through unchanged.

Vectors come from specs/001-hat-desk-buddy/contracts/gadget-injection.md (relay rules 1-3).
The one allowed change is the hello.token rewrite when an upstream token is configured (spike S3).
"""

from __future__ import annotations

import asyncio
import json

import pytest
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from aibuddy.proxy.relay import GadgetRelay

HELLO = {
    "type": "hello", "proto": 1, "device_id": "hg-630dcd2966c43366", "name": "Kitchen Gadget",
    "board": "sim-240x240-round", "firmware": "0.2.0-sim",
    "caps": {"display": {"width": 240, "height": 240, "round": True}},
}
CHALLENGE = {"type": "challenge", "nonce": "AAECAwQFBgcICQoLDA0ODw==", "enrolled": True}
AUTH = {"type": "auth", "mac": "ZmFrZS1tYWM="}
WELCOME = {"type": "welcome", "session": "3f2a9c1b7d4e", "paired": True, "heartbeat_s": 20,
           "server": "hermes", "proto": 1}
AUDIO_FRAME = bytes([0x01, 0x04, 0x02, 0x00]) + bytes(range(64))  # channel 1, stream 4, seq 2


class FakeUpstream:
    """A stand-in for the Hermes gadget plugin hub that records what it receives."""

    def __init__(self):
        self.received: list = []
        self.hellos: list[dict] = []

    async def handler(self, ws):
        await ws.send(json.dumps(CHALLENGE))
        hello = json.loads(await ws.recv())
        self.hellos.append(hello)
        self.received.append(json.dumps(hello))
        await ws.send(json.dumps(WELCOME))  # hub answers with welcome after auth (auth not modelled here)
        async for message in ws:
            self.received.append(message)
            if isinstance(message, bytes):
                await ws.send(message)  # echo binary media back to the device
            else:
                await ws.send(message)


@pytest.fixture
async def upstream():
    hub = FakeUpstream()
    server = await serve(hub.handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield hub, f"ws://127.0.0.1:{port}/gadget"
    finally:
        server.close()
        await server.wait_closed()


async def _start_relay(upstream_url, upstream_token=None):
    relay = GadgetRelay(upstream_url=upstream_url, upstream_token=upstream_token)
    server = await serve(relay.handle, "127.0.0.1", 0)
    return server, f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/gadget"


async def test_handshake_frames_are_relayed_unchanged(upstream):
    hub, upstream_url = upstream
    server, relay_url = await _start_relay(upstream_url)
    try:
        async with connect(relay_url) as device:
            challenge = json.loads(await device.recv())
            assert challenge == CHALLENGE
            await device.send(json.dumps(HELLO))
            await device.send(json.dumps(AUTH))
            welcome = json.loads(await device.recv())
            assert welcome == WELCOME
        assert hub.hellos[0] == HELLO  # hello reached the hub byte-for-byte equivalent (no token configured)
    finally:
        server.close()
        await server.wait_closed()


async def test_binary_media_frames_pass_through_both_ways(upstream):
    hub, upstream_url = upstream
    server, relay_url = await _start_relay(upstream_url)
    try:
        async with connect(relay_url) as device:
            await device.recv()  # challenge
            await device.send(json.dumps(HELLO))
            await device.recv()  # welcome
            await device.send(AUDIO_FRAME)
            echoed = await device.recv()
            assert echoed == AUDIO_FRAME
        assert AUDIO_FRAME in hub.received
    finally:
        server.close()
        await server.wait_closed()


async def test_unknown_json_messages_are_relayed_unchanged(upstream):
    hub, upstream_url = upstream
    server, relay_url = await _start_relay(upstream_url)
    try:
        custom = {"type": "audio.start", "id": "a4", "stream": 4, "rate": 16000,
                  "format": "pcm16", "mode": "hold"}
        async with connect(relay_url) as device:
            await device.recv()
            await device.send(json.dumps(HELLO))
            await device.recv()
            await device.send(json.dumps(custom))
            assert json.loads(await device.recv()) == custom
    finally:
        server.close()
        await server.wait_closed()


async def test_hello_token_is_set_from_upstream_token_when_configured(upstream):
    hub, upstream_url = upstream
    server, relay_url = await _start_relay(upstream_url, upstream_token="s3-secret")
    try:
        async with connect(relay_url) as device:
            await device.recv()
            await device.send(json.dumps({**HELLO, "token": "device-stale"}))
            await device.recv()
        assert hub.hellos[0]["token"] == "s3-secret"
        assert {k: v for k, v in hub.hellos[0].items() if k != "token"} == HELLO
    finally:
        server.close()
        await server.wait_closed()


async def test_failed_upstream_handshake_closes_the_device_with_1011():
    async def refuse(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(b"HTTP/1.1 500 Internal Server Error\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()
        writer.close()

    bad = await asyncio.start_server(refuse, "127.0.0.1", 0)
    bad_url = f"ws://127.0.0.1:{bad.sockets[0].getsockname()[1]}/gadget"
    server, relay_url = await _start_relay(bad_url)
    try:
        async with connect(relay_url) as device:
            with pytest.raises(ConnectionClosed) as info:
                await device.recv()
            assert info.value.rcvd is not None and info.value.rcvd.code == 1011
    finally:
        server.close()
        await server.wait_closed()
        bad.close()
        await bad.wait_closed()


async def test_relay_offers_the_protocol_subprotocol_to_the_upstream():
    """The Hermes gadget hub rejects a handshake that does not offer hermes-gadget.v1 (HTTP 400)."""
    seen = {}

    async def strict_hub(ws):
        if ws.subprotocol != "hermes-gadget.v1":
            await ws.close(1002, "subprotocol required")
            return
        seen["ok"] = True
        await ws.send(json.dumps(CHALLENGE))
        await ws.recv()  # hello
        await ws.send(json.dumps(WELCOME))
        await ws.wait_closed()

    from websockets.asyncio.server import ServerConnection  # noqa: F401  (documentation of the type)
    hub = await serve(strict_hub, "127.0.0.1", 0, subprotocols=["hermes-gadget.v1"])
    hub_url = f"ws://127.0.0.1:{hub.sockets[0].getsockname()[1]}/gadget"
    server, relay_url = await _start_relay(hub_url)
    try:
        async with connect(relay_url) as device:
            assert json.loads(await device.recv()) == CHALLENGE
        assert seen.get("ok") is True
    finally:
        server.close()
        await server.wait_closed()
        hub.close()
        await hub.wait_closed()
