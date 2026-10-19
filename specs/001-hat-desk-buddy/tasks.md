# Tasks: AI Buddy — Multi-Persona Desk Companion

**Input**: Design documents from `/specs/001-hat-desk-buddy/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Requested. The approval state machine (Principle II) is test-first: its tests are written and seen failing before implementation. Other stories include tests where they protect contracts.

**Organization**: Spikes resolve open unknowns first. Tasks are then grouped by user story (P1, P2, P3) so each story is independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US6 from spec.md
- Spike tasks are a separate phase and have no story label

## Path Conventions

Single Python project per plan.md: `src/aibuddy/`, `tests/`, `hats/` at repository root. Spike outputs live in `specs/001-hat-desk-buddy/spikes/`.

---

## Phase 0: Spikes (resolve open unknowns before implementation)

**Purpose**: Each spike answers one question from research.md and records the answer. Spikes must finish before the phases that depend on them.

**Status**: answered from source and docs on 2026-10-19; live checks are listed in each spike file.

**Done when**: each spike file states the observed answer, the method used, and the design change (if any) it forces.

- [x] T001 [P] Spike S1: measure the image box the SpotPear 1.28" profile reports in `caps.display.image`, using the SDK simulator's `sim-466x466-round` profile and the SpotPear profile in its docs; record in `specs/001-hat-desk-buddy/spikes/S1-image-box.md`
- [x] T002 [P] Spike S2: measure Claude Code `PermissionRequest` hook timeout and crash behaviour on the installed Claude Code version using a throwaway hook script that sleeps past the timeout and exits non-zero; record in `specs/001-hat-desk-buddy/spikes/S2-hook-timeout.md` — docs-verified; live run skipped at the user's request (Claude Code auth in this shell not signed in), still to confirm
- [x] T003 [P] Spike S3: determine whether the Hermes Gadget plugin accepts a relayed `hello.token` or needs the proxy to present its own `GADGET_ACCESS_TOKEN`, by running `hermes-gadget devserver` with and without the token set; record in `specs/001-hat-desk-buddy/spikes/S3-token-relay.md`
- [x] T004 [P] Spike S4: determine when a `transcript` message arrives relative to Hermes acting on the same utterance, using the SDK dev server with a recorded voice message; record in `specs/001-hat-desk-buddy/spikes/S4-transcript-timing.md`
- [x] T005 Update `specs/001-hat-desk-buddy/research.md` and `specs/001-hat-desk-buddy/plan.md` with the answers from T001–T004, and note any design change (for example image size, hook timeout margin, token handling, transcript-based deny) in both

**Checkpoint**: all four spikes are recorded and the plan reflects them. Phase 1 may start.

---

## Phase 1: Setup (project initialization)

**Purpose**: Empty Python project, tooling, and layout from plan.md.

- [x] T006 Create the package skeleton under `src/aibuddy/` with empty modules `core/__init__.py`, `proxy/__init__.py`, `bridge/__init__.py`, `hats/__init__.py`, `brain/__init__.py`, and `cli.py`
- [x] T007 Create `pyproject.toml` declaring the `aibuddy` package, Python 3.10+, runtime deps (`websockets`, `pyyaml`, `Pillow`) and dev deps (`pytest`, `pytest-asyncio`), plus an `aibuddy` console script (the `aibuddy-hook` script is added with T027, once its module exists)
- [x] T008 [P] Create test layout `tests/unit/`, `tests/contract/`, `tests/integration/`, `tests/fixtures/` with `tests/conftest.py` configuring pytest-asyncio
- [x] T009 [P] Add `.gitignore` entries for `.venv/`, `build/`, and any local config or token files, so no secrets land in the repo, in `.gitignore`
- [x] T010 [P] Create `tests/fixtures/stop.json` and `tests/fixtures/bash-permission.json` matching the examples in `specs/001-hat-desk-buddy/quickstart.md`

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: Shared core that every story uses. No story work begins until this is done.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete.

- [x] T011 [P] Write unit tests for the event model (types, urgency, summary length ≤ 120, redaction) in `tests/unit/test_event.py`
- [x] T012 [P] Write unit tests for the redaction function (secret-looking tokens removed from summaries) in `tests/unit/test_redaction.py`
- [x] T013 Implement the `Event` and `Session` entities from data-model.md in `src/aibuddy/core/events.py`, making T011 pass
- [x] T014 Implement redaction in `src/aibuddy/core/redaction.py`, making T012 pass
- [x] T015 [P] Write contract tests for the gadget relay rules (handshake passed through unchanged, binary frames passed through unchanged) in `tests/contract/test_gadget_relay.py` using recorded vectors from `specs/001-hat-desk-buddy/contracts/gadget-injection.md`
- [x] T016 Implement the upstream and device WebSocket relay without injection in `src/aibuddy/proxy/relay.py`, making T015 pass
- [x] T017 [P] Write unit tests for the `Brain` interface contract (pass-through brain forwards and StubBrain scripts replies) in `tests/unit/test_brain.py`
- [x] T018 Implement the `Brain` interface, `HermesPassThrough`, and `StubBrain` in `src/aibuddy/brain/base.py`, `src/aibuddy/brain/hermes.py`, and `src/aibuddy/brain/stub.py`, making T017 pass
- [x] T019 Implement config loading (upstream URL, listen address, hats dir) with defaults bound to loopback in `src/aibuddy/core/config.py`

**Checkpoint**: relay and core models pass their tests. User stories can start.

---

## Phase 3: User Story 1 — See my coding agent's state at a glance (Priority: P1) 🎯 MVP

**Goal**: The buddy's face and status reflect Claude Code events within 2 seconds, and shows a disconnected state when nothing is connected.

**Independent Test**: With the SDK dev server and simulator, fire `aibuddy-hook Stop` and `aibuddy-hook PreToolUse`, and see working and done states change on screen (quickstart §2).

### Tests for User Story 1

- [x] T020 [P] [US1] Write unit tests for the status-to-face mapping (event type → face state, including disconnected) in `tests/unit/test_status_mapping.py`
- [x] T021 [P] [US1] Write contract tests for `/v1/event` request and response (204, token required, malformed body ignored) in `tests/contract/test_event_endpoint.py`, from `specs/001-hat-desk-buddy/contracts/hook-bridge.md`
- [x] T022 [P] [US1] Write integration test: fake device receives `status` and `display` after a posted event, via the proxy in `tests/integration/test_status_flow.py`

### Implementation for User Story 1

- [x] T023 [US1] Implement status-to-face mapping in `src/aibuddy/core/status.py`, making T020 pass
- [x] T024 [US1] Implement the loopback HTTP endpoint with bearer token auth for `/v1/event` in `src/aibuddy/bridge/server.py`, making T021 pass
- [x] T025 [US1] Implement token file creation (mode 0600) at `~/.config/aibuddy/token` in `src/aibuddy/bridge/token.py`
- [x] T026 [US1] Implement the injection of `status` and `display` messages into the device leg in `src/aibuddy/proxy/inject.py`, making T022 pass
- [x] T027 [US1] Implement the `aibuddy-hook` CLI for status events (reads stdin JSON, posts to the endpoint, always exits 0) in `src/aibuddy/bridge/hook_cli.py`
- [x] T028 [US1] Implement `aibuddy run` in `src/aibuddy/cli.py` to start the proxy and endpoint together
- [x] T029 [US1] Implement the disconnected state: when the device is not connected, the status endpoint records the last event and the face returns to disconnected on reconnect, in `src/aibuddy/core/status.py` — done: the tracker reports the stale transition once, `announce_staleness` pushes a `Disconnected` status frame, the device watcher in `aibuddy run` checks every 15 s, and reconnecting devices replay the current state.

**Checkpoint**: US1 works in the simulator (quickstart §2). This is the MVP.

---

## Phase 4: User Story 2 — Approve or deny agent actions with a touch (Priority: P1)

**Goal**: Permission requests show a summary on the device; approve only on explicit touch or button, deny on touch, button or voice; every other path defers to the computer.

**Independent Test**: quickstart §3. Yes produces `allow`, no produces `deny`, timeout produces no output.

**Test-first**: the state machine tests in T030–T035 are written and must fail (red) before T036 starts.

### Tests first for User Story 2 (approval state machine, Principle II)

- [ ] T030 [P] [US2] Write state machine tests for `pending → approved` only on explicit approve in `tests/unit/test_approval_state.py`
- [ ] T031 [P] [US2] Write state machine tests for `pending → denied` on explicit deny (touch, button, or voice deny phrase) in `tests/unit/test_approval_state.py`
- [ ] T032 [P] [US2] Write state machine tests asserting `pending → deferred` on timeout, device offline, proxy error, malformed answer, and superseded or withdrawn requests in `tests/unit/test_approval_state.py`
- [ ] T033 [P] [US2] Write state machine tests asserting a voice transcript can never produce `approved`, in `tests/unit/test_approval_state.py`
- [ ] T034 [P] [US2] Write state machine tests asserting high-risk or multi-line requests have no approve path and go straight to `deferred`, in `tests/unit/test_approval_state.py`
- [ ] T035 [P] [US2] Write state machine tests asserting terminal states are final and late answers are ignored, in `tests/unit/test_approval_state.py`
- [ ] T036 [P] [US2] Write contract tests for `/v1/approval` (long-poll, outcome values, bearer token) in `tests/contract/test_approval_endpoint.py`
- [ ] T037 [P] [US2] Write contract tests for `aibuddy-hook PermissionRequest` output rules: `allow` only on approved, `deny` only on denied, no output otherwise, never `updatedInput` or `updatedPermissions`, in `tests/contract/test_permission_hook_output.py`
- [ ] T038 [P] [US2] Write integration test for the device approval flow (fake device answers `bb-` prompt with yes/no; Hermes prompt replies are relayed untouched) in `tests/integration/test_approval_flow.py`

### Implementation for User Story 2 (after T030–T038 fail)

- [ ] T039 [US2] Implement the ApprovalRequest state machine in `src/aibuddy/core/approval.py`, making T030–T035 pass
- [ ] T040 [US2] Implement the `/v1/approval` long-poll endpoint in `src/aibuddy/bridge/server.py`, making T036 pass
- [ ] T041 [US2] Implement the `aibuddy-hook PermissionRequest` path with fail-closed output rules in `src/aibuddy/bridge/hook_cli.py`, making T037 pass
- [ ] T042 [US2] Implement `bb-` prompt injection and `prompt.reply` consumption (reserved prefix, not forwarded to Hermes) in `src/aibuddy/proxy/inject.py` and `src/aibuddy/proxy/relay.py`, making T038 pass
- [ ] T043 [US2] Implement one-outstanding-prompt queueing per device (oldest first, `prompt.close` on withdrawal) in `src/aibuddy/core/approval.py`
- [ ] T044 [US2] Implement the risk classifier and summary builder (tool name plus truncated, redacted input; never the raw input) in `src/aibuddy/core/summary.py`
- [ ] T045 [US2] Implement voice-deny handling: a `transcript` matching a deny phrase while pending resolves as denied, per the timing from spike T004, in `src/aibuddy/proxy/observe.py`

**Checkpoint**: US2 works in the simulator (quickstart §3). Every non-explicit path defers.

---

## Phase 5: User Story 3 — Swap personalities with hats (Priority: P2)

**Goal**: Named hats change wording, images, voice settings, and reactions. Hats are plain-file folders that add without code changes.

**Independent Test**: quickstart §4. `aibuddy hat use sentinel` changes wording and images, and a broken hat falls back to default.

### Tests for User Story 3

- [ ] T046 [P] [US3] Write unit tests for hat manifest validation (format version, unknown keys warned, missing faces fall back) in `tests/unit/test_hat_loader.py`
- [ ] T047 [P] [US3] Write contract tests for the hat pack format against `specs/001-hat-desk-buddy/contracts/hat-pack.md` in `tests/contract/test_hat_pack.py`
- [ ] T048 [P] [US3] Write unit tests for the reaction template rendering (`{session}`, `{tool}`, `{summary}` only; no code execution) in `tests/unit/test_templates.py`

### Implementation for User Story 3

- [ ] T049 [US3] Implement the hat loader and validator in `src/aibuddy/hats/loader.py`, making T046 and T047 pass
- [ ] T050 [US3] Implement reaction rendering with a restricted template engine in `src/aibuddy/hats/templates.py`, making T048 pass
- [ ] T051 [US3] Implement PNG to RGB565 conversion, fitted to the device's reported image box, in `src/aibuddy/hats/faces.py` (depends on spike T001)
- [ ] T052 [US3] Implement manual hat switching (`aibuddy hat use <id>`) and active hat storage in `src/aibuddy/hats/active.py` and `src/aibuddy/cli.py`
- [ ] T053 [P] [US3] Create the `default` hat in `hats/default/hat.yaml` with `hats/default/faces/` images
- [ ] T054 [P] [US3] Create the `geek` hat in `hats/geek/hat.yaml`, `persona.md`, and `faces/`
- [ ] T055 [P] [US3] Create the `coach` hat in `hats/coach/hat.yaml`, `persona.md`, and `faces/`
- [ ] T056 [P] [US3] Create the `sentinel` hat in `hats/sentinel/hat.yaml`, `persona.md`, and `faces/`
- [ ] T057 [US3] Implement `aibuddy hats --check` reporting broken hats and the fallback in `src/aibuddy/cli.py`

**Checkpoint**: US3 works. Two hats differ visibly for the same event (SC-004).

---

## Phase 6: User Story 4 — Talk to my buddy (Priority: P2)

**Goal**: Hold talk, speak, release, and hear and read the reply in the active hat's voice. Cancel stops speech.

**Independent Test**: With voice configured in Hermes, ask a question and receive a spoken and displayed reply; cancel mid-reply.

### Tests for User Story 4

- [ ] T058 [P] [US4] Write integration test that talk-audio frames pass through unchanged and the reply `reply` and `audio` messages reach the device, in `tests/integration/test_voice_relay.py`
- [ ] T059 [P] [US4] Write integration test that `cancel` relays to Hermes and stops speech, in `tests/integration/test_cancel.py`

### Implementation for User Story 4

- [ ] T060 [US4] Ensure the relay preserves binary audio channel frames in both directions in `src/aibuddy/proxy/relay.py`, making T058 pass
- [ ] T061 [US4] Implement the no-voice-engine fallback: when Hermes sends text only, show text and a notice explaining voice is not configured, in `src/aibuddy/proxy/inject.py`
- [ ] T062 [US4] Map hat voice settings to Hermes voice options passed through, in `src/aibuddy/brain/hermes.py`
- [ ] T063 [US4] Implement cancel relay (device `cancel` to Hermes) in `src/aibuddy/proxy/relay.py`, making T059 pass

**Checkpoint**: US4 works with Hermes voice configured. Text-only fallback works without it.

---

## Phase 7: User Story 5 — Proactive, polite updates (Priority: P3)

**Goal**: Non-urgent events respect quiet hours and do-not-disturb. Urgent items stay visible without sound.

**Independent Test**: enable quiet hours, fire a non-urgent event (no speech, shown visually) and an approval (shown visually without sound).

### Tests for User Story 5

- [ ] T064 [P] [US5] Write unit tests for quiet-hours policy (speak suppressed, urgent still shown, held items surfaced later) in `tests/unit/test_quiet_hours.py`

### Implementation for User Story 5

- [ ] T065 [US5] Implement the quiet-hours and do-not-disturb policy in `src/aibuddy/core/policy.py`, making T064 pass
- [ ] T066 [US5] Wire the policy into the reaction path so speak flags are suppressed while quiet, in `src/aibuddy/hats/templates.py` and `src/aibuddy/proxy/inject.py`

**Checkpoint**: US5 works.

---

## Phase 8: User Story 6 — Run it on cheap real hardware (Priority: P3)

**Goal**: A documented path from a new SpotPear 1.28" device to a connected "Ready" buddy, plus a porting guide.

**Independent Test**: follow the setup guide on a clean device and reach a connected Ready state.

- [ ] T067 [US6] Write the device setup guide `docs/setup-device.md`, pointing at the SDK installer for flashing and the AI Buddy listen address for connection
- [ ] T068 [P] [US6] Write the porting guide `docs/porting.md` for other boards, referencing the SDK porting docs
- [ ] T069 [US6] Add a `aibuddy doctor` command in `src/aibuddy/cli.py` that checks the listen address, token file, and upstream reachability

**Checkpoint**: US6 documented and checkable.

---

## Final Phase: Polish & Cross-Cutting Concerns

- [ ] T070 [P] Write README with vision, quickstart, and credits to RegeneratusLabs/physical-hermes, the Hermes Gadget SDK, and xiaozhi-esp32 in `README.md`
- [ ] T071 [P] Add `THIRD_PARTY_NOTICES.md` listing the SDK (MIT) and confirming no code is copied, in `THIRD_PARTY_NOTICES.md`
- [ ] T072 Run the full test suite `pytest tests/` and fix any failures in the affected modules
- [ ] T073 Validate every step in `specs/001-hat-desk-buddy/quickstart.md` by hand and update the document if a command differs
- [ ] T074 Re-run the constitution check in `specs/001-hat-desk-buddy/plan.md` against the implemented code and record any deviation

---

## Dependencies & Execution Order

### Phase dependencies

- **Spikes (Phase 0)**: no dependencies; T001–T004 run in parallel, T005 after them.
- **Setup (Phase 1)**: after spikes, so spike answers can shape the layout.
- **Foundational (Phase 2)**: after Setup; blocks all user stories.
- **User stories (Phase 3+)**: after Foundational. US1 and US2 are both P1; US2 depends on US1's endpoint (T024). US3 depends on spike T001. US4 depends on US1 relay. US5 depends on US2 and US3. US6 can run once US1 works.
- **Polish**: after the stories it covers.

### Within each story

- Tests are written first and fail before implementation starts (especially US2).
- Entities before services, services before endpoints.

### Parallel opportunities

- Spikes T001–T004 in parallel.
- Foundational tests T011, T012, T015, T017 in parallel.
- US2 state machine tests T030–T038 in parallel.
- Hat pack directories T053–T056 in parallel.

## Implementation Strategy

### MVP first

1. Phase 0 spikes, then Phase 1 and Phase 2.
2. Phase 3 (US1): status on the simulator. Stop here and validate.
3. Phase 4 (US2): approvals. Constitution Principle II must hold here before anything else ships.
4. Then US3, US4, US5, US6 in order.

### Notes

- Each task names an exact file path so it can be executed without more context.
- Commit after each task or logical group, with Conventional Commits messages.
