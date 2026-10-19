# Porting AI Buddy to another board

AI Buddy does not contain firmware. Porting a board means porting the Hermes Gadget SDK's device
firmware, and then pointing AI Buddy at it. AI Buddy itself needs no change.

## What AI Buddy needs from the device

The device must speak the Hermes Gadget protocol v1 (subprotocol `hermes-gadget.v1`). The
[protocol reference](https://github.com/Adolanium/hermes-gadget-sdk/blob/main/docs/protocol.md) lists the
messages. AI Buddy uses these:

- the handshake (`hello`, `challenge`, `auth`, `welcome`),
- `status`, `display`, and `prompt` / `prompt.reply` for the buddy's own frames,
- binary channel 2 (RGB565 images) sized to the device's reported image box.

## Steps

1. **Port the firmware.** Follow the SDK's [porting guide](https://github.com/Adolanium/hermes-gadget-sdk/blob/main/docs/porting.md)
   for your board. Its hardware validation table lists what has been tested.
2. **Check the image box.** Read `caps.display.image` from the device's `hello`. Hat faces are scaled into
   that box automatically, but very small boxes make faces hard to read. The 1.28" round board gives
   169 × 122 px (spike S1).
3. **Point AI Buddy at the device.** Run `aibuddy run` and connect the board to `ws://<host>:8770/gadget`.
4. **Check with `aibuddy doctor`,** then test a `Stop` event and a permission prompt.

## Round and square screens

Faces are designed for round screens. On a square panel, the image is centred and the caption text is the
same, so the face still reads. Add a face set per screen shape under `hats/<hat>/faces/` if the default
looks wrong.

## Limits

- Voice depends on speech-to-text and text-to-speech that Hermes provides. A board without a speaker shows
  replies as text only.
- Hardware ports are experimental until the SDK's verification table links a physical report.
