"""Generation of the application icon (``assets/icon.ico``)."""

from __future__ import annotations

import struct
from pathlib import Path

import pygame

from fruit_knight.rendering.procedural import paint_fruit

ICON_SIZES = (16, 32, 48, 64)


def build_icon_surface(size: int) -> pygame.Surface:
    """Draw the procedural icon: an apple on a dark rounded tile.

    :param size: icon edge in pixels.
    :type size: int
    :return: icon surface with alpha.
    :rtype: pygame.Surface
    """
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(surf, (24, 28, 56), surf.get_rect(), border_radius=max(2, size // 5))
    pygame.draw.rect(surf, (255, 171, 64), surf.get_rect(), max(1, size // 16), border_radius=max(2, size // 5))
    inner = int(size * 0.72)
    fruit = paint_fruit("apple", (229, 57, 53), (inner, inner))
    surf.blit(fruit, fruit.get_rect(center=(size // 2, size // 2)))
    return surf


def _dib_entry(surface: pygame.Surface) -> bytes:
    """Encode a surface as an ICO bitmap entry (32-bit BGRA plus AND mask).

    :param surface: square surface with alpha.
    :type surface: pygame.Surface
    :return: DIB payload.
    :rtype: bytes
    """
    w, h = surface.get_size()
    header = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    raw = pygame.image.tobytes(surface, "BGRA")
    rows = [raw[y * w * 4:(y + 1) * w * 4] for y in range(h)]
    pixels = b"".join(reversed(rows))  # bitmaps are stored bottom-up
    mask = bytes(((w + 31) // 32 * 4) * h)
    return header + pixels + mask


def ensure_icon(path: Path) -> Path:
    """Create a valid multi-size ``.ico`` file when it does not exist.

    :param path: destination file.
    :type path: pathlib.Path
    :return: input path, guaranteed to exist.
    :rtype: pathlib.Path
    """
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = [_dib_entry(build_icon_surface(s)) for s in ICON_SIZES]
    offset = 6 + 16 * len(entries)
    directory, blobs = b"", b""
    for size, data in zip(ICON_SIZES, entries):
        directory += struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(data), offset + len(blobs))
        blobs += data
    path.write_bytes(struct.pack("<HHH", 0, 1, len(entries)) + directory + blobs)
    return path
