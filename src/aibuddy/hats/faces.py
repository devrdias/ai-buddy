"""Turn a hat's PNG face into what the device draws: RGB565 that fits the image box (T051)."""

from __future__ import annotations

import io
import struct


from PIL import Image

BOX = (169, 122)  # the SpotPear 1.28" round board's image box (spike S1)
CHUNK_BYTES = 4096
DEFAULT_TTL_S = 30
CHANNEL_IMAGE = 0x02


def png_to_rgb565(source: bytes | str, box: tuple[int, int] = BOX) -> tuple[int, int, bytes]:
    """Fit the picture inside ``box`` keeping its shape, and pack it as RGB565 little-endian.

    The device centres the returned area in its image box, so only the fitted pixels are sent.
    """
    image = Image.open(io.BytesIO(source) if isinstance(source, bytes) else source).convert("RGB")
    image.thumbnail(box, Image.LANCZOS)
    raw = image.tobytes()
    payload = bytearray()
    for i in range(0, len(raw), 3):
        r, g, b = raw[i], raw[i + 1], raw[i + 2]
        payload += struct.pack("<H", ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3))
    return image.width, image.height, bytes(payload)


def image_frames(*, stream: int, width: int, height: int, payload: bytes,
                 ttl_s: int = DEFAULT_TTL_S) -> list[dict | bytes]:
    """image.start, binary channel-2 chunks, image.end (contracts/gadget-injection.md, protocol.md)."""
    frames: list[dict | bytes] = [{"type": "image.start", "stream": stream, "width": width, "height": height,
                                   "format": "rgb565", "ttl_s": ttl_s}]
    for seq, offset in enumerate(range(0, len(payload), CHUNK_BYTES)):
        header = bytes([CHANNEL_IMAGE, stream]) + struct.pack("<H", seq & 0xFFFF)
        frames.append(header + payload[offset:offset + CHUNK_BYTES])
    frames.append({"type": "image.end", "stream": stream})
    return frames


def face_frames(path: str, stream: int) -> list[dict | bytes]:
    width, height, payload = png_to_rgb565(path)
    return image_frames(stream=stream, width=width, height=height, payload=payload)
