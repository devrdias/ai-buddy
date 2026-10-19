"""Contract: POST /v1/approval long-polls until the device answers or the request times out (T036)."""

from __future__ import annotations

import asyncio

import pytest
from aiohttp.test_utils import TestClient, TestServer

from aibuddy.bridge.server import make_app
from aibuddy.core.approval import ApprovalBroker

TOKEN = "test-token-123"


@pytest.fixture
async def stack():
    frames: list[dict] = []
    broker = ApprovalBroker(on_prompt=frames.append, on_close=frames.append)
    app = make_app(token=TOKEN, on_event=lambda e: None, broker=broker)
    async with TestClient(TestServer(app)) as client:
        yield client, broker, frames


def _auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def _body(**overrides) -> dict:
    body = {"session_id": "abc", "cwd": "/tmp/demo", "tool_name": "Bash",
            "tool_input": {"command": "npm test"}, "timeout_s": 5}
    body.update(overrides)
    return body


async def test_missing_token_is_rejected(stack):
    client, _, _ = stack
    resp = await client.post("/v1/approval", json=_body())
    assert resp.status == 401


async def test_malformed_body_is_rejected(stack):
    client, _, _ = stack
    resp = await client.post("/v1/approval", data=b"nope", headers=_auth())
    assert resp.status == 400


async def test_device_approve_returns_approved(stack):
    client, broker, _ = stack

    async def device_taps_yes():
        while not broker.active_id:
            await asyncio.sleep(0.01)
        broker.answer(broker.active_id, approve=True, source="button")

    asyncio.create_task(device_taps_yes())
    resp = await client.post("/v1/approval", json=_body(), headers=_auth())
    assert resp.status == 200
    assert await resp.json() == {"outcome": "approved", "reason": ""}


async def test_no_answer_times_out_as_deferred(stack):
    client, _, frames = stack
    resp = await client.post("/v1/approval", json=_body(timeout_s=0.2), headers=_auth())
    assert await resp.json() == {"outcome": "deferred", "reason": "timeout"}
    assert frames[-1]["type"] == "prompt.close"


async def test_high_risk_request_is_deferred_at_once(stack):
    client, _, frames = stack
    resp = await client.post("/v1/approval", json=_body(tool_input={"command": "rm -rf /"}), headers=_auth())
    assert await resp.json() == {"outcome": "deferred", "reason": "approve on computer"}
    assert frames == []  # nothing is shown on the device for a request that cannot be approved there
