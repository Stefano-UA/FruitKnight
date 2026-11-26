"""Cached pygame fonts."""

from __future__ import annotations

import pygame

FONT_CANDIDATES = "segoeui,helveticaneue,arial,dejavusans,freesans"


class FontCache:
    """Lazily creates fonts by size and weight."""

    def __init__(self) -> None:
        """Create empty cache."""
        self._fonts: dict[tuple[int, bool], pygame.font.Font] = {}

    def get(self, size: int, bold: bool = False) -> pygame.font.Font:
        """Fetch a font.

        :param size: font height in pixels.
        :type size: int
        :param bold: use bold weight.
        :type bold: bool
        :return: font object.
        :rtype: pygame.font.Font
        """
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = pygame.font.SysFont(FONT_CANDIDATES, size, bold=bold)
        return self._fonts[key]

    def text(self, text: str, size: int, color: tuple[int, int, int], bold: bool = False) -> pygame.Surface:
        """Render anti-aliased text.

        :param text: string to render.
        :type text: str
        :param size: font height in pixels.
        :type size: int
        :param color: text colour.
        :type color: tuple[int, int, int]
        :param bold: use bold weight.
        :type bold: bool
        :return: rendered surface.
        :rtype: pygame.Surface
        """
        return self.get(size, bold).render(text, True, color)

    def draw_centered(self, surface: pygame.Surface, text: str, size: int, color: tuple[int, int, int], center: tuple[float, float], bold: bool = True, shadow: bool = True) -> pygame.Rect:
        """Draw text centred on a point, optionally with a drop shadow.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param text: string to draw.
        :type text: str
        :param size: font height in pixels.
        :type size: int
        :param color: text colour.
        :type color: tuple[int, int, int]
        :param center: centre position.
        :type center: tuple[float, float]
        :param bold: use bold weight.
        :type bold: bool
        :param shadow: draw a dark shadow below the text.
        :type shadow: bool
        :return: rectangle covered by the text.
        :rtype: pygame.Rect
        """
        img = self.text(text, size, color, bold)
        rect = img.get_rect(center=(int(center[0]), int(center[1])))
        if shadow:
            surface.blit(self.text(text, size, (0, 0, 0), bold), rect.move(2, 2))
        surface.blit(img, rect)
        return rect
