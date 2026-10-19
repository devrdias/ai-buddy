"""Integration: approval from a device through the relay, and Hermes prompts left alone (T038)."""

from __future__ import annotations

import asyncio
import json

from aiohttp.test_utils import TestClient, TestServer
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from aibuddy.bridge.server import make_app, device_reply_handler
from aibuddy.core.approval import ApprovalBroker
from aibuddy.proxy.inject import Injector
from aibuddy.proxy.relay import GadgetRelay

from tests.contract.test_gadget_relay import CHALLENGE, FakeUpstream, HELLO, WELCOME

TOKEN = "test-token-123"


async def _read_until(ws, predicate, timeout=3.0):
    async def loop():
        while True:
            message = json.loads(await ws.recv())
            if predicate(message):
                return message
    return await asyncio.wait_for(loop(), timeout)


async def test_device_approval_flows_to_the_hook_and_hermes_prompts_pass_through():
    hub = FakeUpstream()
    upstream = await serve(hub.handler, "127.0.0.1", 0)
    upstream_url = f"ws://127.0.0.1:{upstream.sockets[0].getsockname()[1]}/gadget"

    injector = Injector()
    broker = ApprovalBroker(on_prompt=injector.publish_prompt, on_close=injector.clear_prompt)
    relay = GadgetRelay(upstream_url=upstream_url, injector=injector,
                        reply_handler=device_reply_handler(broker))
    relay_server = await serve(relay.handle, "127.0.0.1", 0)
    relay_url = f"ws://127.0.0.1:{relay_server.sockets[0].getsockname()[1]}/gadget"
    bridge = TestClient(TestServer(make_app(token=TOKEN, on_event=lambda e: None, broker=broker)))
    await bridge.start_server()
    try:
        async with connect(relay_url) as device:
            await device.recv()  # challenge
            await device.send(json.dumps(HELLO))
            await device.recv()  # welcome

            hook_call = asyncio.create_task(bridge.post(
                "/v1/approval", json={"session_id": "abc", "tool_name": "Bash",
                                      "tool_input": {"command": "npm test"}, "timeout_s": 10},
                headers={"Authorization": f"Bearer {TOKEN}"}))
            prompt = await _read_until(device, lambda m: m.get("type") == "prompt")
            assert prompt["id"].startswith("bb-")
            assert prompt["title"] == "Bash"

            # Hermes asks its own question at the same time; the reply must reach Hermes untouched.
            hermes_reply = json.dumps({"type": "prompt.reply", "id": "q1", "answer": "yes"})
            await device.send(hermes_reply)
            await device.send(json.dumps({"type": "prompt.reply", "id": prompt["id"], "answer": "yes"}))

            resp = await hook_call
            assert await resp.json() == {"outcome": "approved", "reason": ""}
            await asyncio.sleep(0.1)
            forwarded = [m for m in hub.received if isinstance(m, str) and '"prompt.reply"' in m]
            assert forwarded == [hermes_reply]  # byte-for-byte: Hermes receives exactly what the device sent
    finally:
        await bridge.close()
        relay_server.close()
        upstream.close()
