"""Command-line entry point: ``aibuddy run`` starts the device relay and the local bridge endpoint."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

from aiohttp import web
from websockets.asyncio.server import serve

from . import __version__
from .bridge.server import announce_staleness, make_app, publish_event
from .bridge.token import DEFAULT_TOKEN_PATH, load_or_create_token
from .core.config import Config, ConfigError, load_config
from .core.status import StatusTracker
from .proxy.inject import Injector
from .proxy.relay import GadgetRelay


STALENESS_CHECK_S = 15.0


async def _watch_staleness(tracker: StatusTracker, injector: Injector) -> None:
    while True:
        await asyncio.sleep(STALENESS_CHECK_S)
        announce_staleness(tracker, injector, now=time.time())


async def _run(config: Config, token_path: Path) -> None:
    token = load_or_create_token(token_path)
    injector = Injector()
    tracker = StatusTracker()
    relay = GadgetRelay(upstream_url=config.upstream_url, upstream_token=config.upstream_token,
                        injector=injector)
    app = make_app(token=token, on_event=lambda event: publish_event(event, tracker=tracker, injector=injector))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", config.bridge_port).start()
    async with serve(relay.handle, config.listen_host, config.listen_port):
        print(f"aibuddy {__version__}: devices on ws://{config.listen_host}:{config.listen_port}/gadget, "
              f"bridge on http://127.0.0.1:{config.bridge_port}/v1/event, upstream {config.upstream_url}",
              flush=True)
        watcher = asyncio.create_task(_watch_staleness(tracker, injector))
        try:
            await asyncio.Future()
        finally:
            watcher.cancel()
            await runner.cleanup()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aibuddy", description="AI Buddy desk companion")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="start the device relay and the local hook bridge")
    run.add_argument("--config", type=Path, help="YAML config file (environment variables override it)")
    run.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_PATH)
    args = parser.parse_args(argv)
    if args.command != "run":
        parser.print_help()
        return 0
    try:
        config = load_config(file=args.config)
    except ConfigError as exc:
        print(f"aibuddy: {exc}", file=sys.stderr)
        return 2
    try:
        asyncio.run(_run(config, args.token_file))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
