# Contract: Claude Code hook bridge

## Claude Code configuration (written by `aibuddy install-hooks`, never silently)
Hooks of type `command` calling `aibuddy-hook <event>` for: `SessionStart`, `UserPromptSubmit`,
`PreToolUse`, `PostToolUse`, `Stop`, `Notification`, and `PermissionRequest`. Status hooks SHOULD be
non-blocking and fast. `PermissionRequest` sets an explicit `timeout` slightly above the approval timeout (the default is 600 s), and MUST NOT set `onFailure` (spike S2).

## Local endpoint (loopback only)
`POST http://127.0.0.1:<port>/v1/event` and `POST /v1/approval`, header `Authorization: Bearer <token from ~/.config/aibuddy/token>` (file mode 0600).

### `/v1/event` request
```json
{"event": "Stop", "session_id": "abc", "cwd": "/path/to/project", "summary": "optional short text"}
```
Response `204`. Errors never block Claude Code: the CLI exits 0 with no output.

### `/v1/approval` request
```json
{"session_id": "abc", "cwd": "/path/to/project", "tool_name": "Bash", "tool_input": {"command": "npm test"}}
```
Response (long-poll up to `timeout_s`):
```json
{"outcome": "approved" | "denied" | "deferred", "reason": "optional"}
```

## `aibuddy-hook PermissionRequest` output rules (fail-closed)
| Service outcome | Hook stdout | Effect |
|---|---|---|
| `approved` (explicit device approve) | `{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}` | tool proceeds, subject to deny/ask rules |
| `denied` | `{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"deny","message":"Denied from AI Buddy"}}}` | tool blocked |
| `deferred`, timeout, service unreachable, bad response, any exception | *no output, exit 0* | Claude Code shows its normal permission prompt |

Rules: the CLI never emits `allow` from a default branch; no `updatedInput` or `updatedPermissions` are
ever returned (so a device approval cannot rewrite the command or add rules). The summary sent to the
device is built from `tool_name` and a truncated, redacted `tool_input`, never the raw input.

## Security
- Loopback bind and bearer token; no CORS; reject requests without the token.
- Redaction runs in the service before any text is sent to a device or written to the log.
