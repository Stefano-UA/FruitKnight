"""Full-screen overlays: countdown and pause."""

from __future__ import annotations

import math

import pygame

from fruit_knight.rendering.draw_utils import alpha_rect
from fruit_knight.rendering.fonts import FontCache


class CountdownOverlay:
    """Large pre-match / resume countdown."""

    def __init__(self, fonts: FontCache) -> None:
        """Create overlay.

        :param fonts: font cache.
        :type fonts: fruit_knight.rendering.fonts.FontCache
        """
        self.fonts = fonts

    def draw(self, surface: pygame.Surface, remaining: float, title: str, subtitle: str = "") -> None:
        """Draw the countdown number with a pulsing ring.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param remaining: seconds left (rounded up for display).
        :type remaining: float
        :param title: headline above the number.
        :type title: str
        :param subtitle: hint below the number.
        :type subtitle: str
        """
        w, h = surface.get_size()
        cx, cy = w // 2, h // 2
        number = max(1, math.ceil(remaining))
        phase = remaining - math.floor(remaining)  # 1 -> 0 within each second
        radius = int(120 + 40 * (1 - phase))
        pygame.draw.circle(surface, (255, 171, 64), (cx, cy), radius, 6)
        size = int(190 * (0.85 + 0.15 * phase))
        self.fonts.draw_centered(surface, str(number), size, (255, 255, 255), (cx, cy))
        self.fonts.draw_centered(surface, title, 44, (255, 171, 64), (cx, cy - 210))
        if subtitle:
            self.fonts.draw_centered(surface, subtitle, 24, (236, 239, 244), (cx, cy + 210), bold=False)


class PauseOverlay:
    """Dimmed pause screen with key hints."""

    def __init__(self, fonts: FontCache) -> None:
        """Create overlay.

        :param fonts: font cache.
        :type fonts: fruit_knight.rendering.fonts.FontCache
        """
        self.fonts = fonts

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the pause panel.

        :param surface: target surface.
        :type surface: pygame.Surface
        """
        w, h = surface.get_size()
        alpha_rect(surface, (6, 8, 18), 170, pygame.Rect(0, 0, w, h))
        panel = pygame.Rect(0, 0, 560, 280)
        panel.center = (w // 2, h // 2)
        alpha_rect(surface, (24, 28, 48), 235, panel, 20)
        pygame.draw.rect(surface, (255, 171, 64), panel, 3, border_radius=20)
        self.fonts.draw_centered(surface, "PAUSED", 70, (255, 171, 64), (w // 2, panel.y + 70))
        self.fonts.draw_centered(surface, "Physics, timers and spawners are frozen", 20, (140, 150, 175), (w // 2, panel.y + 124), bold=False)
        self.fonts.draw_centered(surface, "SPACE  -  resume (5 s countdown)", 28, (255, 255, 255), (w // 2, panel.y + 178))
        self.fonts.draw_centered(surface, "ESC  -  quit to main menu", 28, (255, 255, 255), (w // 2, panel.y + 220))
