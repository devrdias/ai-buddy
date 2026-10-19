<!--
Sync Impact Report
- Version change: (unversioned template) → 1.0.0
- Modified principles: none renamed (all five principles newly defined from the blank template)
- Added sections: Core Principles I–V, Security & Privacy Standards, Development Workflow & Quality Gates, Governance
- Removed sections: none
- Deferred items: none
-->

# AI Buddy Constitution

## Core Principles

### I. Local-First
AI Buddy MUST run on the user's own machine and local network. The project MUST NOT depend on any
cloud service operated by the project itself, and the core MUST work with no vendor account. The AI
"brain" MUST sit behind a common interface so it can be swapped (Claude, a local model, another
agent) without changing hats, the device, or the event bridge. Third-party providers a user opts
into are allowed, but never required.

Rationale: privacy, ownership and longevity; the inspiration project proves a useful companion needs
no vendor cloud.

### II. Never Auto-Approve (NON-NEGOTIABLE)
No agent action may be approved without an explicit user response on a paired buddy or the agent's
own prompt. Timeouts, disconnects, malformed messages, crashes and unknown states MUST resolve to
deny or defer-to-the-computer, never approve. Requests too large or risky to summarize at a glance
MUST NOT offer one-tap approval.

Rationale: a physical approve button is only valuable if it can never approve by mistake or default.

### III. Simulator-First
Every P1 and P2 capability MUST work on the desktop simulator before it is built for hardware.
Hardware support is a port of a working core, not the place where behaviour is defined. Core logic
(events, hats, approvals, brain adapters) MUST NOT depend on a specific device.

Rationale: fast iteration, testability in CI, and no blocking on parts arriving.

### IV. Hats Are Plain Files
A hat (persona) MUST be a folder of plain files (YAML or Markdown for configuration and prompts, standard
image or audio formats for assets). Adding, editing or removing a hat MUST NOT require changing or
rebuilding core code. A malformed or missing hat MUST fall back to a built-in default hat and report
the problem rather than crash. Hat format changes MUST be versioned.

Rationale: personas are the project's identity and must be easy to author and share.

### V. Credit and Respect Inspirations
Reused code, firmware, board definitions and ideas MUST be credited in the README and respect their
licences. At minimum: RegeneratusLabs/physical-hermes, the Hermes Gadget SDK (Adolanium), and
xiaozhi-esp32. Licence obligations MUST be checked before copying any file, and copied files MUST
keep their notices.

Rationale: the project stands on community work and must stay legally and ethically clean.

## Security & Privacy Standards

- Buddies MUST be paired with a host; unpaired connections MUST be rejected.
- Only short summaries are shown or spoken; content flagged as secret MUST be redacted. Redaction is
  a safety net, not a guarantee, and docs MUST say so.
- No credentials, tokens or personal or employer data are stored in the repository, hats, logs or
  test fixtures.
- Network exposure is limited to the local network by default; any wider exposure MUST be opt-in and
  documented.
- Events and approvals MUST be logged locally for debugging without recording secrets.

## Development Workflow & Quality Gates

- Test-first for safety-critical logic: the approval flow (Principle II), pairing, and redaction
  MUST have tests written and failing before implementation, including timeout, disconnect and
  error cases.
- Contract tests are required for the event protocol, hat format and brain interface.
- Prefer the simplest design that satisfies the spec (YAGNI); added complexity MUST be justified in
  the plan.
- Work follows Spec Kit: spec, plan, tasks, then implement. Commits follow Conventional Commits and
  releases follow SemVer.
- Every change MUST be checked against this constitution in review.

## Governance

This constitution supersedes other project practices. Amendments require a pull request that states
the change, its rationale and any migration steps, and that updates the Sync Impact Report and
version. The constitution is versioned with SemVer: MAJOR for removing or redefining a principle in
a backward-incompatible way, MINOR for adding a principle or materially expanding guidance, PATCH
for clarifications. Principle II may only be weakened by a MAJOR amendment. Plans and reviews MUST
include a constitution compliance check, and violations MUST be fixed or explicitly justified.

**Version**: 1.0.0 | **Ratified**: 2026-10-19 | **Last Amended**: 2026-10-19
