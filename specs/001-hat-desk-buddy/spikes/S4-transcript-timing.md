# Spike S4: when does a `transcript` arrive relative to Hermes acting?

**Question**: when the user speaks a voice-deny phrase during a pending approval, does the `transcript` message reach the proxy
before Hermes acts on the same utterance, and does it always arrive?

**Method**: source reading of `plugin/adapter.py` (`on_utterance`, `on_processing_start`, `send`, `transcript_echo`).
Not yet run with a recorded voice message against the devserver.

**Findings**
- Device voice: `on_utterance` wraps the WAV as a `VOICE` `MessageEvent` and calls `handle_message`. The gateway then transcribes it.
- `on_processing_start` calls `session.turn_start(turn)` when the gateway begins work on the message.
- The transcript is **not** sent by the adapter directly. It is the gateway's echo line
  (`gateway.voice.transcript_echo_short`, a microphone emoji plus the quoted text), which the gateway sends through
  `adapter.send()`. `send()` detects the echo and calls `session.send_transcript(...)` instead of showing a reply.
- So the transcript depends on the gateway emitting that echo line. If the echo is disabled in Hermes, no transcript is sent.
- The ordering of echo versus `turn_start` versus the agent's first action is set by the gateway, not by the adapter.
  It is not fixed in this code.

**Answer**:
1. The transcript is delivered through `send()`, so it is available only when Hermes emits the echo line.
2. Ordering against the agent's action is not guaranteed by the adapter. A voice deny must therefore be
   treated as best-effort: it resolves the approval as `denied` only if the transcript arrives while the approval is still pending.
3. Voice can never approve. This is unchanged.

**Design change**:
- Voice deny is available only when the transcript echo is enabled. The proxy checks for the transcript and tells the user
  when it is off, instead of failing silently.
- A voice deny also sends `cancel` upstream so the agent stops, when a turn is running, to avoid acting after a refusal.
- Update `contracts/gadget-injection.md` (transcript observation) and data-model approval rules to match.

**Still to verify live**: record one voice utterance against the devserver and log the message order
(`turn.start`, `transcript`, reply). Confirm the echo appears when enabled.

## Live result (2026-10-19): PARTIAL

- Recorded utterance: a 1.5 s WAV fed to the simulator's microphone with `wav` in a headless script, against the devserver.
- Device → server order observed: `audio.start` → `audio.end` → `turn.start` → `status` → `audio.start` (reply speech)
  → `reply.delta` ×12 → `reply` → `turn.end` → `audio.end`.
- **No `transcript` message was sent.** The devserver's `EchoBrain` answers utterances with a fixed "I heard N seconds" reply
  and runs no speech-to-text. So the transcript-before-action question **cannot be answered with the stand-in**.
- To complete: run against real Hermes with speech-to-text enabled and the transcript echo on, then log the message order.
  Until then, keep voice deny best-effort as written in research R6.
