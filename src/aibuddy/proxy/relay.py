"""Transparent relay between a Hermes Gadget device and the Hermes gadget hub.

Frames are passed through unchanged (contracts/gadget-injection.md, relay rules 1-3). The one exception is
``hello.token``: when an upstream token is configured, the relay sets it so the device need not hold it
(research S3). Device identity is still proven by the relayed HMAC handshake, and the token is never logged.

Injected frames (status, cards) start only after the upstream ``welcome`` has reached the device, so the
device always sees the handshake in order.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, WebSocketException

from .inject import Injector

log = logging.getLogger("aibuddy.relay")

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
                log.info("device connected; upstream %s", self.upstream_url)
                await self._pipe(device, upstream)
        except (OSError, WebSocketException) as exc:
            log.warning("upstream unavailable: %s", type(exc).__name__)
            await device.close(INTERNAL_ERROR, "upstream unavailable")
        finally:
            log.info("device disconnected")

    async def _pipe(self, device: Any, upstream: Any) -> None:
        welcomed = asyncio.Event()
        pumps = [
            asyncio.create_task(self._pump(device, upstream, to_upstream=True)),
            asyncio.create_task(self._pump(upstream, device, to_upstream=False, on_frame=welcomed)),
        ]
        if self.injector is not None:
            pumps.append(asyncio.create_task(self._inject(device, welcomed)))
        done, pending = await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            if not task.cancelled() and task.exception() is not None:
                log.warning("relay stopped: %s", type(task.exception()).__name__)
        await device.close()
        await upstream.close()

    async def _inject(self, device: Any, welcomed: asyncio.Event) -> None:
        await welcomed.wait()
        queue = self.injector.attach()
        try:
            while True:
                frame = await queue.get()
                await device.send(json.dumps(frame, separators=(",", ":")))
        except ConnectionClosed:
            return
        finally:
            self.injector.detach(queue)

    async def _pump(self, source: Any, target: Any, *, to_upstream: bool,
                    on_frame: asyncio.Event | None = None) -> None:
        try:
            async for message in source:
                if to_upstream and isinstance(message, str):
                    message = self._rewrite_hello(message)
                if on_frame is not None and isinstance(message, str) and _is_welcome(message):
                    await target.send(message)
                    on_frame.set()
                    continue
                await target.send(message)
        except ConnectionClosed:
            return

    def _rewrite_hello(self, text: str) -> str:
        if not self.upstream_token:
            return text
        frame = _parse_frame(text)
        if frame is None or frame.get("type") != "hello":
            return text
        frame["token"] = self.upstream_token
        return json.dumps(frame, separators=(",", ":"))


def _parse_frame(text: str) -> dict | None:
    try:
        frame = json.loads(text)
    except ValueError:
        return None
    return frame if isinstance(frame, dict) else None


def _is_welcome(text: str) -> bool:
    frame = _parse_frame(text)
    return frame is not None and frame.get("type") == "welcome"
