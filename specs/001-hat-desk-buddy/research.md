# Research: AI Buddy

All items below were resolved from the public Hermes Gadget SDK docs (protocol, architecture, faces,
desktop simulator) and the Claude Code hooks reference, read on 2026-10-19. Items marked **Verify** must
be confirmed by a spike before relying on them.

## R1. How does AI Buddy get its own content onto a device that talks to Hermes?

- **Decision**: A transparent injecting WebSocket proxy. The device connects to AI Buddy; AI Buddy
  connects upstream to the Hermes gadget plugin (`ws://<host>:8765/gadget`). Frames are relayed in both
  directions; AI Buddy additionally sends its own server→device messages (`status`, `display`, `prompt`,
  `notice`, `image.*`) and consumes its own `prompt.reply` answers.
- **Rationale**: The device only connects to one URL, and only the Hermes plugin hub speaks for Hermes.
  A relay keeps Hermes and firmware unmodified, preserves the HMAC handshake (nonce and MAC are
  relayed, so enrollment and pairing still happen with Hermes), and reuses the protocol's yes/no
  `prompt` which the reference firmware already maps to TALK=yes, CANCEL=no.
- **Alternatives**: (a) Patch the Hermes plugin: couples us to its internals and release cadence.
  (b) Run our own hub and call Hermes over its OpenAI-compatible API: loses Hermes's STT/TTS and
  device identity. (c) Fork the firmware: contradicts simulator-first and thin-client principles.
- **Risks**: id collisions on `prompt` ids (use a reserved `bb-` prefix); a Hermes `prompt` and our `prompt`
  active at once (queue ours, one at a time, per protocol rule); heartbeat handling while relaying.
- **Spike S3 (token relay, answered from source)**: the hub rejects a `hello` whose token is wrong when
  `GADGET_ACCESS_TOKEN` is set, so the proxy must present the upstream token. See
  [spikes/S3-token-relay.md](spikes/S3-token-relay.md).

## R2. Claude Code integration for status and approvals

- **Decision**: Claude Code hooks call a tiny CLI (`aibuddy-hook`) that talks to the local AI Buddy
  endpoint. Status uses lifecycle events (`SessionStart`, `UserPromptSubmit`, `PreToolUse`,
  `PostToolUse`, `Stop`, `Notification`); approvals use `PermissionRequest`, which fires only when a
  tool call needs a permission decision.
- **Rationale**: `PermissionRequest` hooks can return `hookSpecificOutput.decision.behavior` of
  `allow` or `deny`. A hook that returns no decision leaves the normal on-screen permission flow
  unchanged, which is exactly our "defer to the computer" fail-safe. Deny and ask rules are still
  evaluated after an `allow`, so we cannot widen permissions.
- **Fail-closed rule**: the CLI emits `allow` only after receiving an explicit `approved` from the
  service. Every other outcome (timeout, service down, malformed reply, device offline, user deny) emits
  `deny` for an explicit user deny, and **no decision at all** otherwise.
- **Spike S2 (answered from docs)**: a timed-out `command` hook has its output discarded, so it renders no
  decision and the normal prompt continues. Exit 0 with a JSON `decision` is the only way to allow or deny. Do not set
  `onFailure: "block"` on this hook, because that would deny. Set an explicit `timeout` above the approval timeout
  (the default is 600 s). See [spikes/S2-hook-timeout.md](spikes/S2-hook-timeout.md).
- **Still to verify live**: a throwaway sleeping hook in a scratch project should show the normal prompt.

## R3. Simulator-first: what is "the simulator"?

- **Decision**: Three layers. (1) A headless Python **fake device** that speaks protocol v1, used by
  all automated tests. (2) The SDK's `hermes-gadget devserver` as a stand-in Hermes upstream (scripted
  echo replies, pairing via `approve <CODE>`). (3) The SDK desktop simulator window (round 466×466
  profile) for visual checks, pointed at AI Buddy instead of Hermes.
- **Rationale**: the SDK already provides a faithful device core and a no-Hermes dev server. Building
  our own window would duplicate it. Needs Python 3.10+, CMake 3.16+, a C++17 compiler and Tk for layer 3
  only; layers 1 and 2 need Python only.
- **Alternatives**: browser-based face simulator: deferred; only worthwhile if the SDK window cannot
  show hat faces (see R4).

## R4. How do hats change the face when faces are compiled into firmware?

- **Finding**: In the SDK the face (idle/blink/talk frames at four sizes) is built into the firmware;
  changing it means rebuilding firmware. There is no runtime face selection. The protocol does allow
  `display` cards and `image.start` frames (RGB565, sized to `caps.display.image`).
- **Decision (v1)**: A hat's visual identity is delivered at runtime as **images and caption text pushed
  by AI Buddy** (a hat provides PNG frames per state; the service converts to RGB565 and sends them
  with `image.start`/`image.end`, and short `status`/`display` text). The stock mascot remains the
  device's own idle face. Hat differentiation in v1 is therefore: pushed state images, wording, voice,
  and reaction rules.
- **Rationale**: honours "no firmware changes" and "hats as plain files".
- **Limits**: image push is not an animation system; expect state-change images, not smooth blinking;
  image box is smaller than the full screen.
- **Follow-up (post-v1)**: upstream or fork a "face pack selected at runtime" feature, and revisit the
  1.28" screen's image box size.
- **Spike S1 (answered from source)**: on the SpotPear 1.28" board the image box is **169 × 122 px**, RGB565,
  centred. It comes from the 169 px inscribed square, a 9 px line height, a 36 px round top band and two 11 px bars.
  See [spikes/S1-image-box.md](spikes/S1-image-box.md). Hat state images must fit this box.

## R5. Local endpoint for the hook bridge

- **Decision**: HTTP on `127.0.0.1` only with a per-install random token in a file readable only by the
  user; the hook CLI reads the token and POSTs JSON. Approvals use a long-poll request that returns when
  the device answers or a timeout elapses.
- **Rationale**: simplest cross-platform channel that survives a hook process per event; loopback only,
  so nothing is exposed to the LAN. Unix socket considered; HTTP chosen for portability and easy tests.
- **Library**: stdlib `http.server` or `aiohttp`; choose `aiohttp` if it is already pulled in by other
  dependencies, else stdlib. Decide at implementation.

## R6. Voice

- **Decision**: no voice code in AI Buddy v1. STT and TTS are whatever the user configured in Hermes
  (spec clarification). Hat voices map to the voice settings Hermes exposes; if none exist, hats differ
  by wording and images only.
- **Voice deny**: the proxy sees the `transcript` message Hermes sends back. While an approval is pending,
  a transcript matching a deny phrase resolves the approval as `deny`. Voice can never approve (spec FR-003).
- **Spike S4 (answered from source)**: the transcript is the gateway's echo line, sent through `send()`, so it
  exists only when the echo is enabled. Its order against Hermes's first action is not fixed by the adapter, so voice
  deny is best-effort: it counts only while the approval is pending. The proxy tells the user when the echo is off, and a
  voice deny also sends `cancel` upstream. See [spikes/S4-transcript-timing.md](spikes/S4-transcript-timing.md).
  **Still to verify live** with a recorded utterance.

## R7. Pairing and trust

- **Decision**: no new pairing mechanism for the device: the proxy relays Hermes's own device
  pairing. For the local hook endpoint, the token file is the credential. For the device leg we bind to
  the LAN interface only when the user opts in; default is loopback for the simulator.
- **Decision (from S3)**: the proxy holds `upstream_token` in its config and writes it into `hello.token` when set;
  otherwise it relays `hello` unchanged. Device identity is still proven by the relayed HMAC, so the proxy never needs the
  device key, and the token value is never logged.

## R8. Licensing

- The SDK is MIT, Hermes Agent is a Nous Research project, and xiaozhi-esp32 is the base of the
  original firmware. We copy no code. We describe the protocol from its public documentation and
  depend on the SDK only as an installed tool. README credits are a required task (constitution V).

## R9. Hat auto-switching, voice approval, bundled voice engine

- Out of scope for v1 per the spec clarifications; no research needed.
