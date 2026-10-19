"""Contract: POST /v1/event on the loopback bridge (contracts/hook-bridge.md)."""

from __future__ import annotations

import pytest
from aiohttp.test_utils import TestClient, TestServer

from aibuddy.bridge.server import make_app

TOKEN = "test-token-123"


@pytest.fixture
async def client():
    received = []
    app = make_app(token=TOKEN, on_event=received.append)
    server = TestServer(app)
    async with TestClient(server) as c:
        c.received = received  # type: ignore[attr-defined]
        yield c


def _auth(token: str = TOKEN) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_valid_event_is_accepted_with_204(client):
    resp = await client.post("/v1/event", json={"event": "Stop", "session_id": "abc", "cwd": "/tmp/demo"},
                             headers=_auth())
    assert resp.status == 204
    assert len(client.received) == 1
    assert client.received[0].type == "done"


async def test_missing_token_is_rejected_with_401(client):
    resp = await client.post("/v1/event", json={"event": "Stop", "session_id": "abc"})
    assert resp.status == 401
    assert client.received == []


async def test_wrong_token_is_rejected_with_401(client):
    resp = await client.post("/v1/event", json={"event": "Stop", "session_id": "abc"}, headers=_auth("nope"))
    assert resp.status == 401


async def test_malformed_body_is_rejected_without_crashing(client):
    resp = await client.post("/v1/event", data=b"not json", headers=_auth())
    assert resp.status == 400
    # The server keeps serving after a bad request.
    ok = await client.post("/v1/event", json={"event": "Stop", "session_id": "abc"}, headers=_auth())
    assert ok.status == 204


async def test_unknown_hook_event_is_rejected_with_400(client):
    resp = await client.post("/v1/event", json={"event": "Nonsense", "session_id": "abc"}, headers=_auth())
    assert resp.status == 400
    assert client.received == []
