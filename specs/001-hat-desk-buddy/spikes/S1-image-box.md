# Spike S1: image box on the SpotPear 1.28" round board

**Question**: what image size can the host push to the SpotPear ESP32-S3-1.28-BOX via `image.start`?

**Method**: source reading of the SDK (`firmware/esp32/main/board.cpp`, `firmware/core/src/ui.cpp`,
`firmware/core/src/app.cpp`, `firmware/core/src/font5x7.cpp`, `plugin/hub.py`). Not yet measured on a device.

**Findings**
- Panel: 240×240 round GC9A01. The `Ui` draws only in the largest square inscribed in the circle:
  `side = 240 * 707 / 1000 = 169`.
- Scale: `s = min(4, max(1, min(169/160, 169/120))) = 1`. The board does not set `font_scale`, so it stays 1.
- Bars: `line_height(1) = kCellHeight(9) * 1 = 9`, so `bar_h = 9 + 2 = 11` (top and bottom bars).
  Round top band: `top_h = max(36, 2*dot_r + 14*s) = 36`, with `dot_r = max(2, 3/2+1) = 2`.
- Main image band: `main_h = 169 - 36 - 11 = 122`.
- The device reports its image box in `hello.caps.display.image` as `width = area width` and `height = main_h`
  (`firmware/core/src/app.cpp` around line 322). The host reads it there; `plugin/hub.py` `image_box()` uses the same value.
- The device rejects an `image.start` whose width is above 169, whose height is above 122, or whose format is not `rgb565`
  (`app.cpp` `h_image_start`).
- Images are centred horizontally and vertically inside the main band.

**Answer**: the image box is **169 × 122 px**, RGB565, centred. Hat state images must be generated at or below that size.

**Design change**: plan and research use 169×122 for hat faces. Earlier "fit to caps.display.image" wording is
replaced by these exact numbers. The face image is a state badge, not a full-screen face.

**Still to verify on hardware**: that the 169×122 value holds with the board's real `font_scale` and that a 169×122 frame looks right on the round panel.

## Live result (2026-10-19)

- Ran the SDK devserver and the headless simulator on `sim-240x240-round` (SDK 0.2.0-sim, built from source).
- Pushed a **169 × 122 RGB565 frame** with the devserver `image` command. The simulator accepted it and switched to the image
  screen (`screen: image`), and `image.start` / `image.end` went out with width 169, height 122.
- Screenshot `169x122` frame centred inside the round panel: `/tmp/sim_frame169.png` (scratch, not committed).
- Caveat: the simulator screenshot also shows a "Settings / Swipe down to close" overlay on the image. That may be
  a simulator overlay rather than a firmware issue. Confirm on the real board.
- Not yet tested: a frame *above* 169 × 122, which the firmware should reject. Real-board check still pending.
