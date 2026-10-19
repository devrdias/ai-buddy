# Feature Specification: AI Buddy — Multi-Persona Desk Companion

**Feature Branch**: `001-hat-desk-buddy` (spec directory only; no git branch created)

**Created**: 2026-10-19

**Status**: Draft

**Input**: User description: "A small desk companion with an expressive animated face, voice, and touch/button input that acts as a physical front-end for a coding agent (Claude Code first). It supports swappable personas called 'hats' (e.g. a geeky coding buddy, a coach, a stern sentinel), each with its own name, face, voice and personality. It shows what the coding agent is doing, lets the user approve or deny agent actions by touch, speaks proactive updates, and runs entirely on the user's own machine and network with no vendor cloud. It must be usable on a desktop simulator before any hardware exists, then on a cheap off-the-shelf voice-robot device. Inspired by RegeneratusLabs/physical-hermes."

## Clarifications

### Session 2026-10-19

- Q: Which AI brain should the buddy use by default? → A: Hermes Agent, following the physical-hermes approach: the device is a thin client and all intelligence runs on the user's own host machine on the local network. Claude Code remains the source of agent status events and approvals; the brain interface stays swappable.
- Q: Where should speech-to-text and text-to-speech run by default? → A: Use whatever speech-to-text and text-to-speech the user already configured in Hermes Agent; AI Buddy ships no voice engine of its own. Per-hat voices are limited to the voice options that configuration exposes.
- Q: Which device should the first version officially support? → A: The SpotPear ESP32-S3 1.28" round-screen AI voice robot used by physical-hermes (already ported, documented and flashable). Other boards (EchoEar 1.85", 1.54" "emo" robot) are future ports via the porting guide.
- Q: What should trigger automatic hat switching in v1? → A: None; v1 supports manual switching only (voice or touch). Automatic rules (time of day, active project, agent events) are deferred to a later version.
- Q: Should the user be able to approve an agent action by voice? → A: No. Approval is by touch or button only; voice may deny or request more detail but MUST NOT approve.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See my coding agent's state at a glance (Priority: P1)

As a developer running a coding agent, I glance at my buddy and immediately know whether the agent is working, waiting for me, finished, or failed — without switching windows.

**Why this priority**: This is the smallest slice that delivers real value and proves the whole pipeline (agent events in, expressive face out). Everything else builds on it.

**Independent Test**: Start the buddy simulator and a coding-agent session; run a task that completes and one that fails. The face changes to match each state within a second or two, with no other feature present.

**Acceptance Scenarios**:

1. **Given** the buddy is connected and idle, **When** the agent starts working on a task, **Then** the face shows a distinct "working" expression.
2. **Given** the agent is working, **When** it finishes successfully, **Then** the face shows a "done" expression and returns to idle after a short time.
3. **Given** the agent is working, **When** a task fails, **Then** the face shows an "error" expression until acknowledged or timed out.
4. **Given** the buddy is not connected to any agent, **When** the user looks at it, **Then** it shows a clear "disconnected" state rather than a stale one.

---

### User Story 2 - Approve or deny agent actions with a touch (Priority: P1)

When the agent asks permission to do something (run a command, edit a file), my buddy shows a short summary and I approve with a tap or button press, or deny with a swipe, button or by speaking.

**Why this priority**: This is the distinctive "physical" capability that separates the project from a plain voice terminal.

**Independent Test**: Trigger a permission request from the agent; approve one and deny another from the buddy alone; confirm the agent proceeds or stops accordingly.

**Acceptance Scenarios**:

1. **Given** the agent requests permission, **When** the buddy shows the summary and the user taps approve, **Then** the agent proceeds.
2. **Given** a pending request, **When** the user swipes to deny, **Then** the agent is told "denied" and does not perform the action.
3. **Given** a pending request, **When** nobody responds within the configured timeout, **Then** the request falls back to the agent's normal on-screen prompt and is never auto-approved.
4. **Given** a request is too large or risky to summarize in a glance, **When** it is shown, **Then** the buddy directs the user to review on the computer instead of offering a one-tap approve.

---

### User Story 3 - Swap personalities with hats (Priority: P2)

I choose between named personas (for example "Geek", "Coach", "Sentinel"), each with its own face style, voice, speaking style, and which events it reacts to. I can switch by voice or touch.

**Why this priority**: This is the project's identity and what makes it unique, but it is meaningful only once the base pipeline works.

**Independent Test**: Install two hats, switch between them, and confirm the face style, voice, wording of the same event, and reaction rules visibly and audibly differ.

**Acceptance Scenarios**:

1. **Given** two hats are installed, **When** the user switches hats, **Then** face, voice and wording of the next event reflect the new hat.
2. **Given** the user requests a hat change by voice or touch, **When** the request is made, **Then** the buddy switches hat and signals the change.
3. **Given** two hats want to speak at once, **When** their priorities differ, **Then** the higher-priority hat speaks and the other stays silent.
4. **Given** a user drops a new hat folder into the hats location, **When** the buddy restarts or reloads, **Then** the hat appears without code changes.

---

### User Story 4 - Talk to my buddy (Priority: P2)

I hold a button, speak, release, and the buddy answers aloud in the current hat's voice, with the reply also shown on screen.

**Why this priority**: Voice is the natural interaction for a physical companion and mirrors the inspiration project, but visual status and approvals already deliver value without it.

**Independent Test**: With only the voice path enabled, ask a question and receive a spoken and displayed answer; cancel a reply mid-way with a gesture.

**Acceptance Scenarios**:

1. **Given** the buddy is idle, **When** the user holds the talk control and speaks, **Then** the speech is transcribed and the reply is spoken and shown.
2. **Given** a reply is being spoken, **When** the user cancels with the cancel gesture, **Then** speech stops immediately.
3. **Given** speech recognition or voice output is not configured, **When** the user talks, **Then** the buddy still shows text replies and explains what is missing.

---

### User Story 5 - Proactive, polite updates (Priority: P3)

The buddy speaks up on its own for important events (long task finished, CI result, reminders), respecting quiet hours and a do-not-disturb mode.

**Why this priority**: Turns the buddy from reactive to ambient, but only valuable once personas and status exist.

**Independent Test**: Enable a proactive event, confirm it is spoken during normal hours and silently shown (or held) during quiet hours.

**Acceptance Scenarios**:

1. **Given** quiet hours are active, **When** a non-urgent event occurs, **Then** it is held and surfaced visually or afterward, not spoken.
2. **Given** an urgent event (a pending approval), **When** quiet hours are active, **Then** it is still shown visibly without sound.

---

### User Story 6 - Run it on cheap real hardware (Priority: P3)

I can move from the desktop simulator to a low-cost voice-robot device by flashing it once, joining it to my Wi-Fi from my phone, and connecting it to my own machine, with no vendor cloud involved.

**Why this priority**: The physical device is the goal but should not block building and validating everything else.

**Independent Test**: Follow the setup guide on a clean device and reach a connected "Ready" state showing a hat's face.

**Acceptance Scenarios**:

1. **Given** a new supported device, **When** the user follows the setup guide, **Then** the device connects and shows Ready within the documented steps.
2. **Given** an unsupported device, **When** the user follows the porting guide, **Then** they can identify what must change to support it.

---

### Edge Cases

- Network drops mid-approval: the pending request must fail safe (denied or deferred to the on-screen prompt), never approved.
- Several agent sessions run at once: the buddy must make clear which session an event or approval belongs to.
- A hat is malformed or missing assets: the buddy falls back to a built-in default hat and reports the problem.
- Very long or sensitive agent output: the buddy shows only a short summary and never shows secrets; full detail stays on the computer.
- Multiple buddies connected: each follows its own hat; approvals can be answered from any one and are then cleared on the others.
- Rapid event bursts: events are coalesced so the face doesn't flicker and speech doesn't queue up for minutes.
- Someone else on the same network tries to connect: the buddy only accepts a paired, authorised host.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display a distinct expressive face state for at least: idle, working, waiting-for-user, done, error, and disconnected.
- **FR-002**: The system MUST receive status events from a coding agent and map them to face states without the user doing anything per task.
- **FR-003**: The system MUST present agent permission requests as a short summary and let the user approve by touch or button only, and deny by touch, button or voice. Voice MUST NOT be able to approve.
- **FR-004**: The system MUST NEVER approve an agent action without an explicit user response, including on timeout, disconnect, or error.
- **FR-005**: The system MUST support multiple personas ("hats"), each defining name, face style, voice, speaking style, event reaction rules and priority.
- **FR-006**: Users MUST be able to add, remove and edit hats as plain files without modifying the core program.
- **FR-007**: Users MUST be able to switch hats manually by voice or touch. Automatic switching rules are out of scope for v1.
- **FR-008**: The system MUST resolve conflicts when multiple hats or events want attention, using explicit priorities.
- **FR-009**: Users MUST be able to hold a talk control, speak, and hear and read a reply in the active hat's voice, using the speech-to-text and text-to-speech already configured in the default brain; AI Buddy MUST NOT bundle its own voice engine in v1.
- **FR-010**: Users MUST be able to cancel a spoken reply with a single gesture.
- **FR-011**: The system MUST support quiet hours and a do-not-disturb mode that suppress speech but keep urgent items visible.
- **FR-012**: The system MUST work fully on a desktop simulator without any hardware.
- **FR-013**: The system MUST run on the user's own machine and local network, and MUST NOT require any third-party cloud service of its own.
- **FR-014**: The system MUST allow the underlying AI "brain" to be swapped (for example Hermes Agent, Claude, a local model) without changing hats or the device, and MUST ship with Hermes Agent as the default brain for voice conversation.
- **FR-019**: The device MUST act only as a thin client (display, microphone, speaker, touch/button); all AI processing, speech handling and agent integration MUST run on the user's host machine.
- **FR-015**: The system MUST require pairing between a buddy and its host and reject unpaired connections.
- **FR-016**: The system MUST limit what is shown or spoken to short summaries and MUST redact content flagged as secret.
- **FR-017**: The system MUST fall back gracefully (text-only, default hat, disconnected face) when speech, a hat, or the network is unavailable.
- **FR-018**: The project MUST provide a setup guide for the first supported device (the SpotPear 1.28" round-screen robot) and a porting guide for other devices.
- **FR-020**: Hat face assets MUST be designed for a round screen and SHOULD scale or adapt to other screen sizes and shapes.

### Key Entities

- **Buddy**: One physical or simulated companion; has a paired host, an active hat, and a connection state.
- **Hat**: A persona bundle: name, face style, voice, speaking style, event reaction rules and priority.
- **Event**: Something that happened on the host (agent started/finished/failed, approval requested, reminder); has type, urgency, session and short summary.
- **Approval Request**: A pending permission question tied to a session, with summary, risk level, timeout and outcome.
- **Session**: One agent run or project context that events belong to.
- **Brain**: The AI that generates replies; interchangeable behind a common interface.
- **Pairing**: The trust relationship between a buddy and a host.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After an agent state change, the buddy's face reflects it in under 2 seconds in at least 95% of cases on a home network.
- **SC-002**: A user can approve or deny a typical agent permission request from the buddy in under 5 seconds from first noticing it.
- **SC-003**: 0 agent actions are ever executed without an explicit user approval across all timeout, disconnect and error test cases.
- **SC-004**: Switching hats produces a visibly and audibly different result for the same event in 100% of the shipped example hats.
- **SC-005**: A new user can create a working custom hat from the documentation in under 15 minutes.
- **SC-006**: A first-time user completes setup from the simulator to a connected buddy in under 10 minutes.
- **SC-007**: A first-time user with a supported device goes from unboxing to a connected "Ready" buddy in under 30 minutes.
- **SC-008**: The simulator-only experience covers all P1 and P2 stories so the project is fully testable without hardware.

## Assumptions

- The primary user is a single developer who already uses a coding agent (Claude Code first) on their own computer.
- The buddy and the host are on the same trusted local network; remote or internet access is out of scope for v1.
- The first supported hardware is the SpotPear ESP32-S3 1.28" round-screen voice robot used by physical-hermes, flashed with its published firmware profile; face designs target a round 1.28" screen. EchoEar and the 1.54" "emo" robot are candidate future ports.
- Hermes Agent is installed and running on the host machine; Claude Code status and approval events come through a separate bridge.
- Speech recognition and voice output are provided by the user's existing Hermes configuration (local or otherwise, their choice); hat voices select among the options that configuration offers.
- Multi-buddy and shared "hat packs" are in scope as design constraints, but full multi-device orchestration is deferred past v1.
- Personal-project use only: work data, customer information and secrets are not expected to flow through the buddy, and redaction is a safety net, not a guarantee.
- Inspiration and credits: RegeneratusLabs/physical-hermes, Hermes Gadget SDK and xiaozhi-esp32; their licences will be respected if code is reused.
