"""Small drawing helpers for translucent shapes."""

from __future__ import annotations

import math

import pygame

Color = tuple[int, int, int]
Vec = tuple[float, float]


def alpha_circle(surface: pygame.Surface, color: Color, alpha: int, center: Vec, radius: float, width: int = 0) -> None:
    """Draw a translucent circle or ring.

    :param surface: target surface.
    :type surface: pygame.Surface
    :param color: RGB colour.
    :type color: tuple[int, int, int]
    :param alpha: opacity in ``[0, 255]``.
    :type alpha: int
    :param center: circle centre.
    :type center: tuple[float, float]
    :param radius: circle radius in pixels.
    :type radius: float
    :param width: ring width, 0 for a filled disc.
    :type width: int
    """
    r = max(1, int(radius))
    tmp = pygame.Surface((2 * r + 4, 2 * r + 4), pygame.SRCALPHA)
    pygame.draw.circle(tmp, (*color, max(0, min(255, alpha))), (r + 2, r + 2), r, width)
    surface.blit(tmp, (int(center[0]) - r - 2, int(center[1]) - r - 2))


def alpha_rect(surface: pygame.Surface, color: Color, alpha: int, rect: pygame.Rect, radius: int = 0) -> None:
    """Draw a translucent rounded rectangle.

    :param surface: target surface.
    :type surface: pygame.Surface
    :param color: RGB colour.
    :type color: tuple[int, int, int]
    :param alpha: opacity in ``[0, 255]``.
    :type alpha: int
    :param rect: rectangle to fill.
    :type rect: pygame.Rect
    :param radius: corner radius.
    :type radius: int
    """
    tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(tmp, (*color, max(0, min(255, alpha))), tmp.get_rect(), border_radius=radius)
    surface.blit(tmp, rect.topleft)


def alpha_line(surface: pygame.Surface, color: Color, alpha: int, a: Vec, b: Vec, width: int) -> None:
    """Draw a translucent line segment with round caps.

    :param surface: target surface.
    :type surface: pygame.Surface
    :param color: RGB colour.
    :type color: tuple[int, int, int]
    :param alpha: opacity in ``[0, 255]``.
    :type alpha: int
    :param a: start point.
    :type a: tuple[float, float]
    :param b: end point.
    :type b: tuple[float, float]
    :param width: line width in pixels.
    :type width: int
    """
    pad = width + 2
    x0, y0 = int(min(a[0], b[0])) - pad, int(min(a[1], b[1])) - pad
    w, h = int(abs(a[0] - b[0])) + 2 * pad, int(abs(a[1] - b[1])) + 2 * pad
    tmp = pygame.Surface((max(1, w), max(1, h)), pygame.SRCALPHA)
    rgba = (*color, max(0, min(255, alpha)))
    pa, pb = (a[0] - x0, a[1] - y0), (b[0] - x0, b[1] - y0)
    pygame.draw.line(tmp, rgba, pa, pb, width)
    pygame.draw.circle(tmp, rgba, pa, width / 2)
    pygame.draw.circle(tmp, rgba, pb, width / 2)
    surface.blit(tmp, (x0, y0))


def arc_points(center: Vec, radius: float, start: float, sweep: float, steps: int = 40) -> list[Vec]:
    """Sample points of a circular arc.

    :param center: arc centre.
    :type center: tuple[float, float]
    :param radius: arc radius.
    :type radius: float
    :param start: start angle in radians (0 = +x, increasing clockwise on screen).
    :type start: float
    :param sweep: angular extent in radians.
    :type sweep: float
    :param steps: number of segments.
    :type steps: int
    :return: polyline points.
    :rtype: list[tuple[float, float]]
    """
    return [
        (center[0] + math.cos(start + sweep * i / steps) * radius, center[1] + math.sin(start + sweep * i / steps) * radius)
        for i in range(steps + 1)
    ]
