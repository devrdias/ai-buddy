# Implementation Plan: AI Buddy — Multi-Persona Desk Companion

**Branch**: `001-hat-desk-buddy` | **Date**: 2026-10-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-hat-desk-buddy/spec.md`

## Summary

AI Buddy is a host-side Python service that sits **between a Hermes Gadget device (or the SDK's
simulator) and the user's Hermes Agent**, speaking the existing Hermes Gadget WebSocket protocol on both
sides. It forwards conversation traffic untouched and **injects** its own content into the device
stream: face/status updates driven by Claude Code hook events, short approval prompts, and hat-styled
wording. A small Claude Code hook bridge turns agent events and `PermissionRequest` calls into local
requests to the service. Hats are plain-file folders. Nothing runs on the device beyond the stock
Hermes Gadget firmware profile for the SpotPear 1.28" robot, so the whole system is developed and
tested against the SDK simulator and a headless fake device first (simulator-first), then flashed.

Spikes S1–S4 are answered in [research.md](research.md) and [spikes/](spikes/): image box 169×122 px, token relay needs `upstream_token`, a timed-out hook yields no decision, and voice deny is best-effort.

Key design choice (see [research.md](research.md) R1): a **transparent injecting proxy** rather than
patching the Hermes plugin or the firmware. It keeps Hermes and the firmware unmodified, preserves device
authentication (the HMAC handshake is relayed, not terminated), and lets approvals use the protocol's
existing yes/no `prompt` message.

## Technical Context

**Language/Version**: Python 3.10+ (matches the Hermes Gadget SDK and plugin)

**Primary Dependencies**: `websockets` (both proxy legs), `pyyaml` (hats), `aiohttp` or stdlib `http.server` for the local hook endpoint (decide in R5), Pillow (hat face images → RGB565), `hermes-gadget-sdk` as an external tool for the simulator and dev server (not vendored)

**Storage**: Files only: hats directory, a small local state/config file, append-only local event log (no secrets)

**Testing**: pytest (+ pytest-asyncio); contract tests against recorded protocol vectors; a headless fake device client; SDK simulator for manual and scripted runs

**Target Platform**: macOS and Linux host (developer machine); device is the stock ESP32-S3 Hermes Gadget firmware or the SDK desktop simulator

**Project Type**: single project (host service + CLI + hook bridge); no firmware in this repo for v1

**Performance Goals**: status change to face update < 2 s on a home LAN (SC-001); approval round trip adds < 500 ms of our own latency

**Constraints**: local network only; fail closed on approvals; short summaries only; pass-through must not alter Hermes traffic it does not own; no cloud dependency of ours

**Scale/Scope**: one host, one to a few buddies, a handful of concurrent Claude Code sessions, ≤ 10 hats

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status (pre) | Status (post design) |
|---|---|---|---|
| I. Local-First | No service of ours in the cloud; brain behind an interface | PASS: all components run on the host; default brain is Hermes | PASS: `Brain` interface in data model; proxy upstream configurable |
| II. Never Auto-Approve | Every non-explicit path resolves to deny or defer | PASS (design intent) | PASS: contract defines `defer` (hook emits no decision) as the default; `allow` only on an explicit device approve; covered by test-first suite |
| III. Simulator-First | P1/P2 work without hardware | PASS | PASS: fake device + SDK simulator are the primary targets; quickstart needs no board |
| IV. Hats Are Plain Files | Folder of plain files, default fallback | PASS | PASS: [contracts/hat-pack.md](contracts/hat-pack.md) |
| V. Credit & Licences | Credits and licence checks | PASS | PASS: SDK used as an external tool, not copied; protocol re-implemented from its public docs; README credit task in tasks |
| Security & Privacy | Pairing, redaction, short summaries | PASS | PASS: device pairing relayed from Hermes; redaction in the summary stage; LAN bind default |

No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-hat-desk-buddy/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── gadget-injection.md   # what we add to / intercept in the device WebSocket stream
│   ├── hook-bridge.md        # Claude Code hook <-> local service
│   └── hat-pack.md           # hat folder format
├── checklists/requirements.md
└── tasks.md                  # created later by /speckit-tasks
```

### Source Code (repository root)

```text
src/aibuddy/
├── core/            # events, sessions, approval state machine, hat engine, redaction, config
├── proxy/           # gadget-protocol injecting proxy (device leg + Hermes leg)
├── bridge/          # local service endpoint + `aibuddy-hook` CLI used by Claude Code hooks
├── hats/            # hat loader/validator, default hat, face renderer (PNG -> RGB565)
├── brain/           # Brain interface; Hermes (pass-through) adapter; stub brain for tests
└── cli.py           # aibuddy run | hats | pair-info | doctor

hats/                # shipped example hats: geek/, coach/, sentinel/, default/
tests/
├── contract/        # protocol vectors, hat format, hook I/O schemas
├── integration/     # fake device <-> proxy <-> stub upstream; hook CLI <-> service
└── unit/
docs/                # setup guide, porting guide, credits
```

**Structure Decision**: single Python project. Firmware, simulator and the Hermes plugin stay in the
upstream SDK and are consumed as external tools (constitution V, simulator-first).

## Complexity Tracking

> No constitution violations to justify.

## Post-implementation constitution check (T074)

Checked against the code on branch `main` at commit 7904d8d:

- **I. Local-First:** PASS. Everything runs on the host. The bridge binds to loopback, and LAN listening needs `AIBUDDY_ALLOW_LAN=true`.
- **II. Never Auto-Approve:** PASS. Only `touch` and `button` approve (`core/approval.py`). Voice can only deny. Timeouts, disconnects and malformed answers defer, and the hook prints no decision for them.
- **III. Simulator-First:** PASS. The approval, status and hat paths were exercised on the simulator before any hardware work.
- **IV. Hats Are Plain Files:** PASS. Hats load from `hats/` with no code changes, and broken hats are reported without crashing.
- **V. Credit and Respect Inspirations:** PASS. Credits are in the README and `THIRD_PARTY_NOTICES.md`. No upstream code is copied.

Open items against the plan: none. T061 (text-only fallback notice) is built. T062 (hat voice mapping) is closed as not applicable for v1, because Hermes exposes no per-chat voice option.

