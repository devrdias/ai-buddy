# Quickstart: validate the simulator-first MVP

Goal: prove the pipeline end to end with no hardware and no real Hermes.

## Prerequisites
- Python 3.10+; `pip install -e ".[dev]"` in this repo (after implementation)
- For the visual check only: the Hermes Gadget SDK checkout built per its desktop guide (CMake, C++17 compiler, Tk)

## 1. Automated checks (headless, no hardware)
```bash
pytest tests/contract tests/integration
```
Expected: handshake relay, approval state machine (approve, deny, timeout, disconnect, late answer), hat loading with fallback, and hook output rules all pass.

## 2. Status pipeline against a stand-in Hermes
1. Start the SDK dev server (scripted Hermes): `hermes-gadget devserver --pairing`
2. Start AI Buddy pointed at it: `aibuddy run --upstream ws://127.0.0.1:8765/gadget --listen 127.0.0.1:8770`
3. Start the SDK simulator pointed at AI Buddy: `hermes-gadget sim --url ws://127.0.0.1:8770/gadget --board sim-466x466-round`; approve pairing with `approve <CODE>`
4. Fire a sample event: `aibuddy-hook Stop < tests/fixtures/stop.json`
Expected (US1): the simulator shows the hat's "done" wording/image within 2 s, then returns to idle.

## 3. Approvals
1. Fire `aibuddy-hook PermissionRequest < tests/fixtures/bash-permission.json`
2. In the simulator, press TALK (yes) → hook prints an `allow` decision; repeat and press CANCEL (no) → `deny`; repeat and wait → no output (deferred).
Expected (US2, SC-003): no path prints `allow` unless yes was pressed.

## 4. Hats
`aibuddy hat use sentinel` and repeat step 2: wording and image differ from `geek` (US3, SC-004). `aibuddy hats --check` reports a deliberately broken hat and the default hat takes over.

## 5. Real Claude Code (optional)
`aibuddy install-hooks --dry-run` shows the exact hook config; apply it, run a Claude Code task that needs a permission, and answer on the simulator.

## 6. Real device (later)
Follow `docs/setup-device.md` (flash the SpotPear 1.28" profile via the SDK installer, join Wi-Fi, point it at the AI Buddy listen address).
