# Contract: Gadget stream injection

Protocol reference: Hermes Gadget protocol v1 (subprotocol `hermes-gadget.v1`, JSON text frames plus
4-byte-header binary frames). AI Buddy relays everything it does not own.

## Relay rules
1. Handshake (`challenge`, `auth`, `welcome`, `pairing`, `paired`) is relayed unchanged both ways. `hello` is relayed unchanged, except that when `upstream_token` is configured the proxy sets `hello.token` to it (spike S3).
2. Binary frames (audio, firmware) are relayed unchanged both ways. Firmware offers (`ota.*`) are relayed; AI Buddy never initiates one.
3. Server→device and device→server JSON messages not listed below are relayed unchanged.
4. If the upstream connection drops, AI Buddy closes the device leg so the device reconnects; it never fabricates `welcome`.

## Messages AI Buddy sends to the device (server→device)
| Message | Use |
|---|---|
| `status` | Short working-state phrase in the active hat's wording; empty string clears it |
| `display` | Short hat-styled card (`ttl_s` set), e.g. "Done: 12 tests passed" |
| `notice` | Transient one-liner for low-urgency events |
| `image.start` / binary channel 2 / `image.end` | Hat state image (RGB565, fitted to `caps.display.image`) |
| `prompt` | Approval question. `id` MUST start with `bb-`. `title` = tool name, `text` = redacted one-line summary, `ttl_s` = approval timeout |
| `prompt.close` | Withdraw our prompt (timeout, superseded, answered by the computer) |

## Messages AI Buddy consumes (device→server)
| Message | Handling |
|---|---|
| `prompt.reply` with `id` starting `bb-` | Resolve the matching ApprovalRequest: `yes` → approved, `no` → denied. NOT forwarded to Hermes |
| `prompt.reply` with any other id | Relayed to Hermes |
| `state.display_sleeping` | Relayed; AI Buddy also records it and holds image/card pushes while the screen is dark |

## Messages AI Buddy observes (read-only)
| Message | Use |
|---|---|
| `transcript` (server→device) | While an approval is pending, a deny phrase resolves it as denied. Never resolves as approved. Best-effort: exists only when Hermes's transcript echo is enabled (spike S4). A voice deny also sends `cancel` upstream |
| `welcome`, `turn.*` | Connection and activity state for hat reactions |

## Ordering and concurrency
- Only one AI Buddy `prompt` outstanding per device at a time; others queue and are served oldest first.
- If Hermes has a `prompt` active, ours waits (and its ttl is counted from when it is shown).
- Press-debounce of the first 0.6 s is the firmware's behaviour; AI Buddy additionally ignores an answer that arrives before the prompt was sent.

## Test vectors
Contract tests record and replay these sequences: handshake relay, approve, deny, timeout, device
disconnect mid-prompt, answer after `prompt.close`, id collision attempt (device sends a `bb-` reply
with no pending request: ignored).
