"""Integration: an agent event reaches a device as status and display frames (US1 independent test)."""

from __future__ import annotations

import asyncio
import json

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from aibuddy.bridge.server import publish_event
from aibuddy.core.events import Event
from aibuddy.core.status import StatusTracker
from aibuddy.proxy.inject import Injector
from aibuddy.proxy.relay import GadgetRelay

from tests.contract.test_gadget_relay import CHALLENGE, FakeUpstream, HELLO, WELCOME  # noqa: F401


async def _read_until(ws, predicate, timeout=3.0):
    async def loop():
        while True:
            message = json.loads(await ws.recv())
            if predicate(message):
                return message
    return await asyncio.wait_for(loop(), timeout)


async def test_done_event_shows_status_and_display_on_device():
    hub = FakeUpstream()
    upstream = await serve(hub.handler, "127.0.0.1", 0)
    upstream_url = f"ws://127.0.0.1:{upstream.sockets[0].getsockname()[1]}/gadget"

    injector = Injector()
    tracker = StatusTracker(stale_after_s=300)
    relay = GadgetRelay(upstream_url=upstream_url, injector=injector)
    relay_server = await serve(relay.handle, "127.0.0.1", 0)
    relay_url = f"ws://127.0.0.1:{relay_server.sockets[0].getsockname()[1]}/gadget"
    try:
        async with connect(relay_url) as device:
            await device.recv()  # challenge
            await device.send(json.dumps(HELLO))
            await device.recv()  # welcome

            event = Event.create(type="done", session_id="abc", summary="Tests passed")
            publish_event(event, tracker=tracker, injector=injector)

            status = await _read_until(device, lambda m: m.get("type") == "status")
            display = await _read_until(device, lambda m: m.get("type") == "display")
            assert status["text"]
            assert display["title"]
            assert "Tests passed" in display["body"]
    finally:
        relay_server.close()
        upstream.close()


async def test_going_stale_pushes_a_disconnected_face_once_and_replays_on_reconnect():
    from aibuddy.bridge.server import announce_staleness

    injector = Injector()
    tracker = StatusTracker(stale_after_s=300)
    old = Event.create(type="working", session_id="abc")
    publish_event(old, tracker=tracker, injector=injector)
    queue = injector.attach()
    while not queue.empty():
        queue.get_nowait()  # drop the replayed working frames

    assert announce_staleness(tracker, injector, now=old.ts + 299) is False
    assert announce_staleness(tracker, injector, now=old.ts + 301) is True
    assert queue.get_nowait() == {"type": "status", "text": "Disconnected"}
    assert announce_staleness(tracker, injector, now=old.ts + 400) is False  # not repeated

    fresh_queue = injector.attach()  # a device that reconnects now sees the disconnected state
    assert fresh_queue.get_nowait() == {"type": "status", "text": "Disconnected"}
