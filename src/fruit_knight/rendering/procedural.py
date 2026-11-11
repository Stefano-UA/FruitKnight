"""Procedural sprite painters used when image files are missing.

Every painter draws on a 3x supersampled canvas and downsamples it, which yields anti-aliased shapes.
"""

from __future__ import annotations

import math
import random

import pygame

Color = tuple[int, int, int]
Size = tuple[int, int]
# Supersampling factor of the painters.
SS = 3


def _canvas(size: Size) -> pygame.Surface:
    """Create transparent supersampled canvas.

    :param size: final sprite size in pixels.
    :type size: tuple[int, int]
    :return: transparent surface ``SS`` times larger.
    :rtype: pygame.Surface
    """
    return pygame.Surface((size[0] * SS, size[1] * SS), pygame.SRCALPHA)


def _finish(big: pygame.Surface, size: Size) -> pygame.Surface:
    """Downsample a supersampled canvas.

    :param big: supersampled surface.
    :type big: pygame.Surface
    :param size: final size in pixels.
    :type size: tuple[int, int]
    :return: anti-aliased sprite with per-pixel alpha.
    :rtype: pygame.Surface
    """
    small = pygame.transform.smoothscale(big, size)
    # Conversion needs an initialised display; headless icon generation skips it.
    return small.convert_alpha() if pygame.display.get_surface() else small


def _mix(a: Color, b: Color, t: float) -> Color:
    """Blend two colours.

    :param a: colour at ``t = 0``.
    :type a: tuple[int, int, int]
    :param b: colour at ``t = 1``.
    :type b: tuple[int, int, int]
    :param t: blend factor.
    :type t: float
    :return: mixed colour.
    :rtype: tuple[int, int, int]
    """
    return tuple(max(0, min(255, int(a[i] + (b[i] - a[i]) * t))) for i in range(3))  # type: ignore[return-value]


def _shade(c: Color, factor: float) -> Color:
    """Brighten or darken a colour.

    :param c: input colour.
    :type c: tuple[int, int, int]
    :param factor: multiplier; below 1 darkens.
    :type factor: float
    :return: scaled colour.
    :rtype: tuple[int, int, int]
    """
    if factor <= 1.0:
        return _mix((0, 0, 0), c, factor)
    return _mix(c, (255, 255, 255), factor - 1.0)


def _alpha_shape(big: pygame.Surface, painter, color: tuple[int, int, int, int]) -> None:
    """Draw a translucent shape that blends with existing pixels.

    :param big: target surface.
    :type big: pygame.Surface
    :param painter: callable ``painter(temp_surface, color)`` drawing the shape.
    :type painter: typing.Callable
    :param color: RGBA colour.
    :type color: tuple[int, int, int, int]
    """
    temp = pygame.Surface(big.get_size(), pygame.SRCALPHA)
    painter(temp, color)
    big.blit(temp, (0, 0))


def shaded_ball(big: pygame.Surface, center: tuple[float, float], radius: float, color: Color) -> None:
    """Draw a sphere with radial shading and a soft outline.

    :param big: supersampled target surface.
    :type big: pygame.Surface
    :param center: sphere centre in canvas pixels.
    :type center: tuple[float, float]
    :param radius: sphere radius in canvas pixels.
    :type radius: float
    :param color: base colour.
    :type color: tuple[int, int, int]
    """
    pygame.draw.circle(big, _shade(color, 0.35), center, radius)
    dark, bright = _shade(color, 0.7), _shade(color, 1.3)
    steps = 20
    for i in range(steps):
        t = i / (steps - 1)
        c = (center[0] - 0.3 * radius * t, center[1] - 0.35 * radius * t)
        pygame.draw.circle(big, _mix(dark, bright, t), c, radius * (0.95 - 0.78 * t))
    gloss = pygame.Rect(0, 0, radius * 0.55, radius * 0.32)
    gloss.center = (center[0] - radius * 0.38, center[1] - radius * 0.45)
    _alpha_shape(big, lambda s, c: pygame.draw.ellipse(s, c, gloss), (255, 255, 255, 120))


def _circle_mask(size: tuple[int, int], center: tuple[float, float], radius: float) -> pygame.Surface:
    """Build white circular mask.

    :param size: canvas size in pixels.
    :type size: tuple[int, int]
    :param center: circle centre.
    :type center: tuple[float, float]
    :param radius: circle radius.
    :type radius: float
    :return: surface opaque white inside the circle.
    :rtype: pygame.Surface
    """
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), center, radius)
    return mask


def _blit_masked(big: pygame.Surface, layer: pygame.Surface, mask: pygame.Surface) -> None:
    """Blit a layer clipped by a mask.

    :param big: target surface.
    :type big: pygame.Surface
    :param layer: surface to clip.
    :type layer: pygame.Surface
    :param mask: alpha mask surface.
    :type mask: pygame.Surface
    """
    layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    big.blit(layer, (0, 0))


def paint_fruit(subtype: str, color: Color, size: Size) -> pygame.Surface:
    """Paint a fruit sprite.

    :param subtype: fruit name selecting decorations (watermelon, coconut, apple, banana, berry).
    :type subtype: str
    :param color: base colour.
    :type color: tuple[int, int, int]
    :param size: sprite size in pixels.
    :type size: tuple[int, int]
    :return: fruit sprite.
    :rtype: pygame.Surface
    """
    big = _canvas(size)
    cx, cy = big.get_width() / 2, big.get_height() / 2
    r = min(cx, cy) * 0.92
    if subtype == "banana":
        _paint_banana(big, (cx, cy), r, color)
        return _finish(big, size)
    shaded_ball(big, (cx, cy), r, color)
    if subtype == "watermelon":
        layer = pygame.Surface(big.get_size(), pygame.SRCALPHA)
        for k in range(-3, 4):
            rect = pygame.Rect(0, 0, r * 0.22, r * 2.2)
            rect.center = (cx + k * r * 0.3, cy)
            pygame.draw.ellipse(layer, (*_shade(color, 0.45), 200), rect)
        _blit_masked(big, layer, _circle_mask(big.get_size(), (cx, cy), r * 0.97))
    elif subtype == "coconut":
        for dx, dy in ((-0.25, -0.15), (0.25, -0.15), (0.0, 0.2)):
            pygame.draw.circle(big, (45, 28, 18), (cx + dx * r, cy + dy * r), r * 0.11)
        layer = pygame.Surface(big.get_size(), pygame.SRCALPHA)
        rng = random.Random(4)
        for _ in range(70):  # husk fibres
            a, d = rng.uniform(0, math.tau), rng.uniform(0.2, 0.95) * r
            p = (cx + math.cos(a) * d, cy + math.sin(a) * d)
            pygame.draw.line(layer, (*_shade(color, 0.5), 150), p, (p[0] + rng.uniform(-r, r) * 0.15, p[1] + rng.uniform(-r, r) * 0.15), max(1, SS))
        _blit_masked(big, layer, _circle_mask(big.get_size(), (cx, cy), r * 0.97))
    elif subtype == "apple":
        pygame.draw.line(big, (92, 58, 30), (cx, cy - r * 0.8), (cx + r * 0.1, cy - r * 1.05), int(r * 0.12))
        leaf = pygame.Rect(0, 0, r * 0.5, r * 0.26)
        leaf.center = (cx + r * 0.32, cy - r * 0.9)
        pygame.draw.ellipse(big, (76, 175, 80), leaf)
    elif subtype == "berry":
        rng = random.Random(9)
        for _ in range(9):
            a, d = rng.uniform(0, math.tau), rng.uniform(0.1, 0.7) * r
            pygame.draw.circle(big, _shade(color, 1.5), (cx + math.cos(a) * d, cy + math.sin(a) * d), r * 0.09)
        for k in range(5):  # green calyx
            a = -math.pi / 2 + k * math.tau / 5
            tip = (cx + math.cos(a) * r * 0.45, cy - r * 0.8 + math.sin(a) * r * 0.2)
            pygame.draw.line(big, (76, 175, 80), (cx, cy - r * 0.8), tip, int(r * 0.12))
    return _finish(big, size)


def _paint_banana(big: pygame.Surface, center: tuple[float, float], r: float, color: Color) -> None:
    """Paint a crescent banana inside a circular footprint.

    :param big: supersampled target surface.
    :type big: pygame.Surface
    :param center: footprint centre.
    :type center: tuple[float, float]
    :param r: footprint radius.
    :type r: float
    :param color: base colour.
    :type color: tuple[int, int, int]
    """
    cx, cy = center
    outer, inner = [], []
    for i in range(41):
        a = math.radians(200 + 140 * i / 40)
        outer.append((cx + math.cos(a) * r * 0.95, cy + 0.4 * r + math.sin(a) * r * 0.95))
        inner.append((cx + math.cos(a) * r * 0.6, cy + 0.55 * r + math.sin(a) * r * 0.6))
    pts = outer + inner[::-1]
    pygame.draw.polygon(big, _shade(color, 0.55), pts)
    shrunk = [(cx + (x - cx) * 0.96, cy + (y - cy) * 0.96) for x, y in pts]
    pygame.draw.polygon(big, color, shrunk)
    pygame.draw.lines(big, _shade(color, 1.4), False, outer[4:-4], int(r * 0.07))
    pygame.draw.circle(big, (92, 58, 30), outer[0], r * 0.09)
    pygame.draw.circle(big, (92, 58, 30), outer[-1], r * 0.09)


def paint_bomb(color: Color, size: Size) -> pygame.Surface:
    """Paint a bomb with cap, fuse and spark.

    :param color: body colour.
    :type color: tuple[int, int, int]
    :param size: sprite size in pixels.
    :type size: tuple[int, int]
    :return: bomb sprite.
    :rtype: pygame.Surface
    """
    big = _canvas(size)
    w, h = big.get_size()
    c = (w / 2, h * 0.58)
    r = min(w, h) * 0.38
    shaded_ball(big, c, r, _mix(color, (70, 75, 95), 0.35))
    cap = pygame.Rect(0, 0, r * 0.55, r * 0.3)
    cap.center = (c[0] + r * 0.2, c[1] - r * 0.98)
    pygame.draw.rect(big, (120, 124, 140), cap, border_radius=int(r * 0.08))
    fuse = [(cap.centerx, cap.top), (cap.centerx + r * 0.2, cap.top - r * 0.35), (cap.centerx + r * 0.55, cap.top - r * 0.4)]
    pygame.draw.lines(big, (200, 170, 110), False, fuse, int(r * 0.1))
    sx, sy = fuse[-1]
    pts = []
    for i in range(16):  # eight-pointed spark
        rad = r * (0.38 if i % 2 == 0 else 0.15)
        a = i * math.tau / 16
        pts.append((sx + math.cos(a) * rad, sy + math.sin(a) * rad))
    pygame.draw.polygon(big, (255, 170, 30), pts)
    pygame.draw.circle(big, (255, 240, 130), (sx, sy), r * 0.11)
    return _finish(big, size)


def paint_holder(color: Color, size: Size, defused: bool) -> pygame.Surface:
    """Paint a holder grenade: timer ring with clock or check icon.

    :param color: ring colour.
    :type color: tuple[int, int, int]
    :param size: sprite size in pixels.
    :type size: tuple[int, int]
    :param defused: draw the defused (check mark) variant.
    :type defused: bool
    :return: holder sprite.
    :rtype: pygame.Surface
    """
    big = _canvas(size)
    cx, cy = big.get_width() / 2, big.get_height() / 2
    r = min(cx, cy) * 0.9
    shaded_ball(big, (cx, cy), r, _mix((40, 44, 60), color, 0.2))
    pygame.draw.circle(big, color, (cx, cy), r * 0.86, int(r * 0.13))
    pygame.draw.circle(big, _shade(color, 0.4), (cx, cy), r * 0.62, max(1, int(r * 0.04)))
    if defused:
        pts = [(cx - r * 0.3, cy), (cx - r * 0.06, cy + r * 0.26), (cx + r * 0.34, cy - r * 0.25)]
        pygame.draw.lines(big, (240, 255, 240), False, pts, int(r * 0.14))
    else:
        pygame.draw.line(big, (240, 240, 245), (cx, cy), (cx, cy - r * 0.38), int(r * 0.1))
        pygame.draw.line(big, (240, 240, 245), (cx, cy), (cx + r * 0.26, cy + r * 0.12), int(r * 0.1))
        pygame.draw.circle(big, color, (cx, cy), r * 0.07)
    return _finish(big, size)


def paint_thrower(color: Color, size: Size) -> pygame.Surface:
    """Paint a thrower grenade with directional chevrons.

    :param color: body colour.
    :type color: tuple[int, int, int]
    :param size: sprite size in pixels.
    :type size: tuple[int, int]
    :return: thrower sprite.
    :rtype: pygame.Surface
    """
    big = _canvas(size)
    cx, cy = big.get_width() / 2, big.get_height() / 2
    r = min(cx, cy) * 0.9
    shaded_ball(big, (cx, cy), r, color)
    pygame.draw.circle(big, _shade(color, 0.4), (cx, cy), r * 0.88, int(r * 0.08))
    for k in range(3):
        y = cy + r * (0.32 - 0.32 * k)
        pts = [(cx - r * 0.38, y + r * 0.16), (cx, y - r * 0.12), (cx + r * 0.38, y + r * 0.16)]
        pygame.draw.lines(big, (245, 250, 255), False, pts, int(r * 0.12))
    return _finish(big, size)


def paint_limiter(kind: str, size: Size) -> pygame.Surface:
    """Paint a horizontal limiter texture whose tip is at the right end.

    :param kind: ``"trunk"`` (wood) or ``"beam"`` (steel).
    :type kind: str
    :param size: texture length and thickness in pixels.
    :type size: tuple[int, int]
    :return: limiter texture.
    :rtype: pygame.Surface
    """
    length, thick = size
    surf = pygame.Surface(size, pygame.SRCALPHA)
    rng = random.Random(21)
    if kind == "trunk":
        base = (121, 85, 52)
        pygame.draw.rect(surf, base, (0, 0, length, thick), border_radius=thick // 3)
        for _ in range(length // 12):  # wood grain
            y = rng.randint(3, thick - 4)
            x = rng.randint(0, length)
            pygame.draw.line(surf, _shade(base, 0.7 if rng.random() < 0.7 else 1.25), (x, y), (min(length, x + rng.randint(20, 90)), y), 1)
        pygame.draw.rect(surf, _shade(base, 0.6), (0, 0, length, thick), 3, border_radius=thick // 3)
        for k in range(1, 5):  # rings on the cut tip
            ring = pygame.Rect(0, 0, thick * 0.5 * (1 - k * 0.2), thick * (1 - k * 0.2))
            ring.midright = (length - 4, thick // 2)
            pygame.draw.ellipse(surf, _shade((190, 150, 100), 1.0 - k * 0.08), ring, 2)
    else:
        base = (110, 120, 135)
        pygame.draw.rect(surf, base, (0, 0, length, thick), border_radius=thick // 4)
        pygame.draw.rect(surf, _shade(base, 1.3), (0, 2, length, thick // 4))
        for x in range(0, length, 26):
            pygame.draw.circle(surf, _shade(base, 0.55), (x + 13, thick // 2), max(2, thick // 9))
        for x in range(length - 90, length - 10, 24):  # hazard stripes near the tip
            pygame.draw.polygon(surf, (255, 193, 7), [(x, thick - 3), (x + 12, thick - 3), (x + 22, 3), (x + 10, 3)])
        pygame.draw.rect(surf, _shade(base, 0.5), (0, 0, length, thick), 2, border_radius=thick // 4)
    return surf


def paint_portal(color: Color, size: Size) -> pygame.Surface:
    """Paint a translucent target zone panel.

    :param color: accent colour.
    :type color: tuple[int, int, int]
    :param size: panel size in pixels.
    :type size: tuple[int, int]
    :return: portal sprite.
    :rtype: pygame.Surface
    """
    w, h = size
    surf = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(surf, (*color, 70), (0, 0, w, h), border_radius=18)
    for i in range(6):  # nested glow frames
        inset = i * 5
        if w > inset * 2 and h > inset * 2:
            pygame.draw.rect(surf, (*_shade(color, 1.0 + i * 0.05), 150 - i * 22), (inset, inset, w - 2 * inset, h - 2 * inset), 3, border_radius=max(4, 18 - i * 2))
    return surf


def paint_heart(size: Size, filled: bool, color: Color = (255, 82, 108)) -> pygame.Surface:
    """Paint a life heart.

    :param size: sprite size in pixels.
    :type size: tuple[int, int]
    :param filled: draw filled heart when True, outline otherwise.
    :type filled: bool
    :param color: fill colour.
    :type color: tuple[int, int, int]
    :return: heart sprite.
    :rtype: pygame.Surface
    """
    big = _canvas(size)
    w, h = big.get_size()
    pts = []
    for i in range(120):
        t = i / 120 * math.tau
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((w / 2 + x / 17 * w * 0.48, h * 0.48 + y / 17 * h * 0.48))
    if filled:
        pygame.draw.polygon(big, _shade(color, 0.55), pts)
        shrunk = [(w / 2 + (x - w / 2) * 0.86, h * 0.48 + (y - h * 0.48) * 0.86) for x, y in pts]
        pygame.draw.polygon(big, color, shrunk)
    else:
        pygame.draw.polygon(big, (120, 126, 150), pts, SS * 2)
    return _finish(big, size)


def paint_background(size: Size) -> pygame.Surface:
    """Paint a dark arcade backdrop with perspective grid.

    :param size: backdrop size in pixels.
    :type size: tuple[int, int]
    :return: opaque background.
    :rtype: pygame.Surface
    """
    w, h = size
    surf = pygame.Surface(size)
    for y in range(h):
        t = y / h
        pygame.draw.line(surf, _mix((10, 12, 28), (34, 24, 64), t), (0, y), (w, y))
    grid = (255, 255, 255, 14)
    overlay = pygame.Surface(size, pygame.SRCALPHA)
    for x in range(0, w, 48):
        pygame.draw.line(overlay, grid, (x, 0), (x, h))
    for y in range(0, h, 48):
        pygame.draw.line(overlay, grid, (0, y), (w, y))
    surf.blit(overlay, (0, 0))
    return surf.convert()


def paint_logo(size: Size, text: str = "FRUIT KNIGHT") -> pygame.Surface:
    """Paint the title logo.

    :param size: logo size in pixels.
    :type size: tuple[int, int]
    :param text: title text.
    :type text: str
    :return: logo sprite.
    :rtype: pygame.Surface
    """
    surf = pygame.Surface(size, pygame.SRCALPHA)
    font = pygame.font.SysFont("impact,arialblack,arial", int(size[1] * 0.78), bold=True)
    shadow = font.render(text, True, (20, 8, 40))
    face = font.render(text, True, (255, 183, 77))
    face_top = font.render(text, True, (255, 236, 179))
    x, y = (size[0] - face.get_width()) // 2, (size[1] - face.get_height()) // 2
    for off in range(6, 0, -1):
        surf.blit(shadow, (x + off, y + off))
    surf.blit(face, (x, y))
    surf.blit(face_top, (x, y - 2), area=pygame.Rect(0, 0, face.get_width(), face.get_height() // 2))
    return surf
