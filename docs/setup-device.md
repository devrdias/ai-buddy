# Set up a device

This guide connects a Hermes Gadget device to AI Buddy. It starts with the simulator, which needs no
hardware, and then covers the SpotPear ESP32-S3 1.28" round robot.

## 1. Check the host

```bash
aibuddy doctor
```

Every line should say `OK`. A `FAIL` line says what to fix. The most common one is the Hermes upstream,
which must be reachable at `AIBUDDY_UPSTREAM_URL` (default `ws://127.0.0.1:8765/gadget`).

## 2. Run the buddy

```bash
aibuddy run
```

The device endpoint listens on `127.0.0.1:8770` and the hook bridge on `127.0.0.1:8771`. Keep this
running.

## 3. Flash the board

Use the Hermes Gadget SDK installer for the SpotPear 1.28" board (profile `spotpear-esp32-s3-1.28-box`).
Follow the SDK's [setup guide](https://github.com/Adolanium/hermes-gadget-sdk/blob/main/docs/setup-board.md).

## 4. Point the board at AI Buddy

Connect the board to Wi-Fi with the SDK's phone setup. Then set its gadget URL to the address where
`aibuddy run` listens: `ws://<your-computer-ip>:8770/gadget`.

Set `AIBUDDY_LISTEN_HOST` to your computer's LAN address and `AIBUDDY_ALLOW_LAN=true`, because the default
listen address is loopback only.

## 5. Check it

- The board shows **Ready** and pairs with the host.
- `aibuddy-hook` with a `Stop` event shows the Done card and the hat's face.
- A permission request shows the prompt. TALK approves and CANCEL denies.

If the board doesn't connect, check the firewall for port 8770 on your computer.
