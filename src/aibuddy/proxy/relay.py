"""Transparent relay between a Hermes Gadget device and the Hermes gadget hub.

Frames are passed through unchanged (contracts/gadget-injection.md, relay rules 1-3). The one exception is
``hello.token``: when an upstream token is configured, the relay sets it so the device need not hold it
(research S3). Device identity is still proven by the relayed HMAC handshake, and the token is never logged.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from .inject import Injector
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

INTERNAL_ERROR = 1011


class GadgetRelay:
    def __init__(self, *, upstream_url: str, upstream_token: str | None = None,
                 injector: Injector | None = None) -> None:
        self.upstream_url = upstream_url
        self.upstream_token = upstream_token
        self.injector = injector

    async def handle(self, device: Any) -> None:
        """Serve one device connection by pairing it with a fresh upstream connection."""
        try:
            async with connect(self.upstream_url) as upstream:
                await self._pipe(device, upstream)
        except OSError:
            await device.close(INTERNAL_ERROR, "upstream unavailable")

    async def _pipe(self, device: Any, upstream: Any) -> None:
        pumps = [
            asyncio.create_task(self._pump(device, upstream, to_upstream=True)),
            asyncio.create_task(self._pump(upstream, device, to_upstream=False)),
        ]
        queue = self.injector.attach() if self.injector else None
        if queue is not None:
            pumps.append(asyncio.create_task(self._inject(queue, device)))
        _, pending = await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        if queue is not None:
            self.injector.detach(queue)
        await device.close()
        await upstream.close()

    async def _inject(self, queue: asyncio.Queue, device: Any) -> None:
        try:
            while True:
                frame = await queue.get()
                await device.send(json.dumps(frame, separators=(",", ":")))
        except ConnectionClosed:
            return

    async def _pump(self, source: Any, target: Any, *, to_upstream: bool) -> None:
        try:
            async for message in source:
                if to_upstream and isinstance(message, str):
                    message = self._rewrite_hello(message)
                await target.send(message)
        except ConnectionClosed:
            return

    def _rewrite_hello(self, text: str) -> str:
        if not self.upstream_token:
            return text
        try:
            frame = json.loads(text)
        except ValueError:
            return text
        if not (isinstance(frame, dict) and frame.get("type") == "hello"):
            return text
        frame["token"] = self.upstream_token
        return json.dumps(frame, separators=(",", ":"))
