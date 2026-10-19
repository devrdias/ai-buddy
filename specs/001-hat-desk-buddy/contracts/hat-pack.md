# Contract: Hat pack format (version 1)

A hat is a folder under `hats/` (or the user hats directory). Only plain files.

```text
hats/geek/
├── hat.yaml        # manifest (required)
├── persona.md      # system prompt / personality text (optional)
└── faces/          # PNG images per state (optional; missing states fall back to the default hat)
    ├── idle.png  working.png  waiting.png  done.png  error.png  disconnected.png
```

## `hat.yaml`
```yaml
format: 1
name: Geek
priority: 50            # higher wins when two hats want attention
persona: persona.md
voice: {}               # passed through to the Hermes voice configuration if supported
reactions:
  - when: done          # session_start|working|tool_use|done|error|waiting|approval_request|notice
    say: "Build's green. Ship it."
    face: done
    speak: false
  - when: error
    say: "Segfault in {session}. Classic."
    face: error
    speak: true
    urgency_min: normal
```

## Rules
- Unknown keys are ignored with a warning; `format` greater than supported skips the hat with a reported error.
- Templates may use `{session}`, `{tool}`, `{summary}` only; no code execution of any kind.
- Image files MUST be PNG, at most 256 KiB each. The service fits each to the device-reported image box (169×122 px on the SpotPear 1.28" board, spike S1).
- A broken hat never crashes the service; the built-in `default` hat is used and the problem is shown in `aibuddy hats --check`.
- Hat switching is manual in v1 (voice or touch trigger → `aibuddy hat use <id>` equivalent); no auto-switch rules.
