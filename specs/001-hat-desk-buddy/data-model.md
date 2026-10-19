# Data Model: AI Buddy

Entities from the spec, with fields, relationships and state rules. Types are descriptive.

## Buddy
- `device_id` (from the Hermes Gadget handshake, e.g. `hg-…`), `name`, `board`, `caps` (display, image box, inputs)
- `connection`: `offline | connecting | online`
- `active_hat`: `Hat.id`
- `paired`: bool (reported by Hermes `welcome`)
- Relationships: has one active Hat; receives many Events; may hold one pending ApprovalRequest on screen

## Hat
- `id` (folder name), `name`, `version` (hat format version), `priority` (int)
- `persona`: prompt text (Markdown file)
- `voice`: optional settings passed through to the Hermes voice configuration
- `faces`: map of state → image file (`idle`, `working`, `waiting`, `done`, `error`, `disconnected`)
- `reactions`: list of rules `{when: event_type, say: template, face: state, speak: bool, urgency_min}`
- Validation: unknown keys ignored with a warning; missing files fall back to the `default` hat's asset; a hat with an invalid manifest is skipped and reported (FR-017)

## Event
- `id`, `ts`, `type` (`session_start | working | tool_use | done | error | waiting | notice | approval_request`)
- `session_id`, `urgency` (`low | normal | urgent`), `summary` (≤ 120 chars, redacted)
- Rules: summaries are produced by the summary stage and redacted before leaving the host process

## Session
- `id` (Claude Code session id), `label` (project directory basename), `last_event`, `state`
- A Buddy shows the most urgent Session; the label is included in approval summaries (edge case: multiple sessions)

## ApprovalRequest
- `id` (`bb-…`), `session_id`, `tool_name`, `summary` (≤ 1 device line, redacted), `risk` (`low | high`), `created`, `timeout_s`
- State machine (every transition tested before implementation, constitution Dev Workflow):

```
pending ──approve (touch/button)──▶ approved   (only path to `allow`)
pending ──deny (touch/button/voice)─▶ denied    (`deny`)
pending ──timeout / device offline / proxy error / malformed answer──▶ deferred  (no decision; Claude Code shows its own prompt)
pending ──superseded by newer request or withdrawn──▶ deferred
```
- Voice deny (spike S4): a `transcript` deny phrase counts only while the request is `pending`. If the transcript echo is off, voice deny is unavailable and the UI says so
- `risk = high` or summary longer than one device line: no approve affordance; device shows "approve on computer" and the request becomes `deferred` immediately (spec US2 scenario 4)
- Terminal states are final; late answers are ignored

## Brain (interface)
- `name`, `converse(text|audio ref) -> reply stream`, `capabilities`
- Default implementation: `HermesPassThrough` (traffic is relayed to the Hermes plugin; no in-process model)
- Test implementation: `StubBrain` (scripted)

## Pairing / Trust
- Device trust is Hermes's own (device key + pairing approval); AI Buddy stores no device keys
- Local hook endpoint trust: random token file with mode 0600
