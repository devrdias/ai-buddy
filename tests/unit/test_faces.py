"""Face conversion (T051): any PNG becomes RGB565 that fits the 169 x 122 image box, centred."""

from __future__ import annotations

import io
import struct

from PIL import Image

from aibuddy.hats.faces import BOX, image_frames, png_to_rgb565


def _png(size, colour=(255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, format="PNG")
    return buf.getvalue()


def test_box_matches_the_spotpear_round_board():
    assert BOX == (169, 122)


def test_large_image_is_scaled_to_fit_the_box_keeping_aspect():
    width, height, payload = png_to_rgb565(_png((400, 200)))
    assert width <= 169 and height <= 122
    assert (width, height) == (169, 85)  # 84.5 rounds up; it still fits the 122-px box
    assert len(payload) == width * height * 2


def test_pixels_are_rgb565_little_endian():
    width, height, payload = png_to_rgb565(_png((1, 1), colour=(255, 0, 0)))
    (value,) = struct.unpack("<H", payload[:2])
    assert value == 0xF800  # pure red in RGB565


def test_image_frames_start_chunks_and_end_follow_the_protocol():
    width, height, payload = png_to_rgb565(_png((169, 122)))
    frames = image_frames(stream=7, width=width, height=height, payload=payload)
    assert frames[0] == {"type": "image.start", "stream": 7, "width": width, "height": height,
                         "format": "rgb565", "ttl_s": 30}
    assert frames[-1] == {"type": "image.end", "stream": 7}
    chunks = frames[1:-1]
    assert all(isinstance(c, bytes) for c in chunks)
    assert all(c[0] == 0x02 and c[1] == 7 for c in chunks)  # channel 2, stream 7
    sequence = [struct.unpack("<H", c[2:4])[0] for c in chunks]
    assert sequence == list(range(len(chunks)))
    assert b"".join(c[4:] for c in chunks) == payload
