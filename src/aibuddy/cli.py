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
from .bridge.server import announce_staleness, device_reply_handler, make_app, publish_event, release_held
from .bridge.token import DEFAULT_TOKEN_PATH, load_or_create_token
from .core.approval import ApprovalBroker
from .core.policy import QuietPolicy
from .hats.active import read_active, write_active
from .hats.loader import load_hats
from .core.config import Config, ConfigError, load_config
from .core.status import StatusTracker
from .proxy.inject import Injector
from .proxy.observe import transcript_observer
from .proxy.relay import SUBPROTOCOL, GadgetRelay


STALENESS_CHECK_S = 15.0


async def _watch_staleness(tracker: StatusTracker, injector: Injector, policy: QuietPolicy,
                           library, active) -> None:
    while True:
        await asyncio.sleep(STALENESS_CHECK_S)
        announce_staleness(tracker, injector, now=time.time())
        release_held(tracker=tracker, injector=injector, policy=policy, now=time.time(),
                     library=library, active=active)


async def _run(config: Config, token_path: Path) -> None:
    token = load_or_create_token(token_path)
    library = load_hats(config.hats_dir)
    policy = QuietPolicy(start=config.quiet_start, end=config.quiet_end)
    injector = Injector()
    tracker = StatusTracker()
    broker = ApprovalBroker(on_prompt=injector.publish_prompt, on_close=injector.clear_prompt)
    relay = GadgetRelay(upstream_url=config.upstream_url, upstream_token=config.upstream_token,
                        injector=injector, reply_handler=device_reply_handler(broker),
                        observer=transcript_observer(broker))
    app = make_app(token=token, broker=broker,
                   on_event=lambda event: publish_event(event, tracker=tracker, injector=injector,
                                                        library=library, active=read_active, policy=policy))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", config.bridge_port).start()
    async with serve(relay.handle, config.listen_host, config.listen_port, subprotocols=[SUBPROTOCOL]):
        print(f"aibuddy {__version__}: devices on ws://{config.listen_host}:{config.listen_port}/gadget, "
              f"bridge on http://127.0.0.1:{config.bridge_port}/v1/event, upstream {config.upstream_url}",
              flush=True)
        watcher = asyncio.create_task(_watch_staleness(tracker, injector, policy, library, read_active))
        try:
            await asyncio.Future()
        finally:
            watcher.cancel()
            await runner.cleanup()


def _hats(args) -> int:
    library = load_hats(args.hats_dir)
    for hat in sorted(library.hats.values(), key=lambda h: (-h.priority, h.id)):
        print(f"{hat.id:<12} {hat.name:<12} priority {hat.priority}")
        for warning in hat.warnings:
            print(f"  warning: {warning}")
    for problem in library.problems:
        print(f"  problem in {problem.hat_id}: {problem.message}")
    return 1 if args.check and library.problems else 0


def _doctor(args) -> int:
    from .doctor import run_checks

    try:
        config = load_config(file=args.config)
    except ConfigError as exc:
        print(f"FAIL  configuration: {exc}")
        return 1
    checks = run_checks(config, token_path=args.token_file, hats_dir=args.hats_dir)
    for name, ok, detail in checks:
        print(f"{'OK  ' if ok else 'FAIL'}  {name}: {detail}")
    return 0 if all(ok for _, ok, _ in checks) else 1


def _use_hat(args) -> int:
    library = load_hats(args.hats_dir)
    if args.hat_id not in library.hats:
        print(f"aibuddy: no hat named {args.hat_id!r} in {args.hats_dir}", file=sys.stderr)
        return 2
    write_active(args.hat_id)
    print(f"active hat: {args.hat_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aibuddy", description="AI Buddy desk companion")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="start the device relay and the local hook bridge")
    run.add_argument("--config", type=Path, help="YAML config file (environment variables override it)")
    run.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_PATH)
    hats = sub.add_parser("hats", help="list hats and report problems")
    hats.add_argument("--hats-dir", type=Path, default=Path("hats"))
    hats.add_argument("--check", action="store_true", help="exit 1 when any hat has a problem")
    doctor = sub.add_parser("doctor", help="check the setup and explain any failure")
    doctor.add_argument("--config", type=Path, help="YAML config file")
    doctor.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_PATH)
    doctor.add_argument("--hats-dir", type=Path, default=Path("hats"))
    use = sub.add_parser("hat", help="choose the active hat")
    use.add_argument("action", choices=["use"])
    use.add_argument("hat_id")
    use.add_argument("--hats-dir", type=Path, default=Path("hats"))
    args = parser.parse_args(argv)
    if args.command == "hats":
        return _hats(args)
    if args.command == "hat":
        return _use_hat(args)
    if args.command == "doctor":
        return _doctor(args)
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
