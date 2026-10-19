# Spike S2: PermissionRequest hook timeout and failure behaviour

**Question**: when a `PermissionRequest` command hook times out, crashes or prints nothing, does Claude Code fall back to its normal permission prompt?

**Method**: Claude Code hooks reference (`https://code.claude.com/docs/en/hooks`), sections Timeouts, Hook failures and
PermissionRequest decision control, read on 2026-10-19. A live run with a throwaway hook has **not** been done yet.

**Findings (documented)**
- Default timeout for `command` hooks is **600 s**. Set an explicit `timeout` in the hook config, slightly above the approval timeout.
- On timeout, Claude Code cancels the hook and **discards its output**, so on most events a timed-out hook renders no decision.
  This means no `allow` and no `deny`, and the normal permission flow continues. That matches our fail-safe.
- Failures (can't start, exit code other than 0 or 2, invalid JSON) count as hook failures. A failed `PermissionRequest` hook
  without `onFailure: "block"` leaves the permission flow unchanged.
- `onFailure: "block"` on `PermissionRequest` **denies** the request. Do **not** set it: our rule is defer (no decision), not deny.
- Exit code 2 is not honoured on `PermissionRequest`. Only a JSON `decision` object changes the outcome.
- Exit 0 with a JSON `decision` is the only way to return `allow` or `deny`.

**Answer**: a timed-out or crashed `PermissionRequest` hook yields no decision, and Claude Code shows its normal prompt.
Our hook must (a) exit 0 on every path, (b) print JSON only for an explicit device approve or deny, and
(c) not set `onFailure`.

**Design change**: the hook config sets `timeout` above the service approval timeout. The service always answers before the
hook timeout, and a timeout falls through to the computer prompt.

**Still to verify live**: run a throwaway hook that sleeps past its timeout in a scratch project and confirm the prompt
appears. Only the docs confirm this so far.

## Live result (2026-10-19): NOT RUN

- Attempted a scratch project in `/tmp/s2proj` with a `PermissionRequest` command hook (`timeout: 5`, script sleeps 30 s).
- `claude -p` failed before any tool call: `Failed to authenticate: OAuth session expired and could not be refreshed`.
  The hook never ran, so there is no timing evidence yet.
- To complete: sign in to Claude Code interactively (`claude`, then `/login`), then rerun the same scratch project.
  The expected result is that the hook is cancelled at about 5 s and the permission prompt still appears.

## Retry (2026-10-19): still NOT RUN

- After the user said they had signed in, reran the same scratch project. `claude -p` still failed with
  `Failed to authenticate: OAuth session expired and could not be refreshed`, and `claude auth status` reports `loggedIn: false`
  in this shell. The hook never ran, so there is still no timing evidence.
- Likely cause: the sign-in went to the desktop app or another environment, not this shell's credentials.
  Sign in from a terminal in this environment (`claude auth login`), then rerun.

## Second retry (2026-10-19): still NOT RUN

- After the user reported a terminal sign-in with `claude auth login`, `claude auth status` in this shell still reports
  `loggedIn: false`, and `claude -p` still fails with `OAuth session expired and could not be refreshed`. This shell does not
  pick up that login. The hook has not run.
- Next step: the user runs the S2 scratch test from a terminal that has the signed-in session, or confirms the credentials
  this shell uses.

