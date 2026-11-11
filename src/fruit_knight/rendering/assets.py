"""Asset manager: loads sprites from disk or falls back to procedural painters."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import pygame

from fruit_knight.utils.paths import resource_path

log = logging.getLogger(__name__)
Size = tuple[int, int]
Painter = Callable[[Size], pygame.Surface]


class AssetManager:
    """Caches sprites; never crashes on missing or corrupt files."""

    def __init__(self, root: Path | None = None) -> None:
        """Create manager.

        :param root: directory that sprite paths are relative to; repository root by default.
        :type root: pathlib.Path | None
        """
        self._root = root or resource_path()
        self._cache: dict[tuple[str, Size, str], pygame.Surface] = {}
        self._originals: dict[str, pygame.Surface | None] = {}
        self.missing: set[str] = set()

    def exists(self, rel_path: str) -> bool:
        """Check whether a sprite file is on disk.

        :param rel_path: path relative to the asset root.
        :type rel_path: str
        :return: True when the file exists.
        :rtype: bool
        """
        return bool(rel_path) and (self._root / rel_path).is_file()

    def _original(self, rel_path: str) -> pygame.Surface | None:
        """Load an image once, returning ``None`` when unavailable.

        :param rel_path: path relative to the asset root.
        :type rel_path: str
        :return: loaded surface or ``None``.
        :rtype: pygame.Surface | None
        """
        if rel_path not in self._originals:
            image = None
            if self.exists(rel_path):
                try:
                    image = pygame.image.load(str(self._root / rel_path)).convert_alpha()
                except (pygame.error, OSError):
                    log.warning("Corrupt sprite '%s'; using procedural fallback", rel_path)
            self._originals[rel_path] = image
        return self._originals[rel_path]

    def get(self, rel_path: str, size: Size, painter: Painter, style: str = "") -> pygame.Surface:
        """Fetch a sprite of the requested size.

        :param rel_path: configured sprite path relative to the asset root.
        :type rel_path: str
        :param size: target size in pixels.
        :type size: tuple[int, int]
        :param painter: procedural fallback receiving the size.
        :type painter: typing.Callable[[tuple[int, int]], pygame.Surface]
        :param style: extra cache key distinguishing fallbacks that share a path.
        :type style: str
        :return: sprite surface.
        :rtype: pygame.Surface
        """
        size = (max(1, int(size[0])), max(1, int(size[1])))
        key = (rel_path, size, style)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        original = self._original(rel_path)
        if original is not None:
            sprite = pygame.transform.smoothscale(original, size)
        else:
            if rel_path:
                self.missing.add(rel_path)
            sprite = painter(size)
        self._cache[key] = sprite
        return sprite

    def rotated(self, sprite: pygame.Surface, degrees: float, step: float = 6.0) -> pygame.Surface:
        """Rotate a sprite using quantised cached angles.

        :param sprite: source sprite.
        :type sprite: pygame.Surface
        :param degrees: counter-clockwise rotation in degrees.
        :type degrees: float
        :param step: angle quantisation in degrees.
        :type step: float
        :return: rotated sprite.
        :rtype: pygame.Surface
        """
        q = round(degrees / step) * step
        key = (f"rot:{id(sprite)}", (int(q) % 360, 0), "")
        cached = self._cache.get(key)
        if cached is None:
            cached = self._cache[key] = pygame.transform.rotate(sprite, q)
        return cached
