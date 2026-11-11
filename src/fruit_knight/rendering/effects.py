"""Visual effects: sliced halves, juice, explosions, popups and slice trails."""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass

import pygame

from fruit_knight.config.schema import GameConfig
from fruit_knight.modes.events import GameEvent
from fruit_knight.rendering.draw_utils import alpha_circle, alpha_line
from fruit_knight.rendering.fonts import FontCache
from fruit_knight.rendering.sprites import SpriteProvider
from fruit_knight.utils.constants import HandState
from fruit_knight.vision.hands import HandSample

Vec = tuple[float, float]
Color = tuple[int, int, int]
# Visual-only constants of the effects.
HALF_GRAVITY = 900.0
HALF_SEPARATION_SPEED = 160.0
HALF_LIFETIME = 1.4
PARTICLE_GRAVITY = 700.0


@dataclass
class _Half:
    """One flying half of a sliced fruit."""

    surface: pygame.Surface
    pos: list[float]
    vel: list[float]
    angle: float
    spin: float
    life: float


@dataclass
class _Particle:
    """Juice or spark particle."""

    pos: list[float]
    vel: list[float]
    color: Color
    life: float
    max_life: float
    radius: float


@dataclass
class _Popup:
    """Floating text."""

    text: str
    pos: list[float]
    color: Color
    life: float
    size: int


@dataclass
class _Ring:
    """Expanding shock ring."""

    pos: Vec
    max_radius: float
    color: Color
    life: float
    max_life: float


def split_sprite(sprite: pygame.Surface, cut_angle: float) -> list[tuple[pygame.Surface, Vec]]:
    """Cut a sprite in two along a line through its centre.

    :param sprite: sprite to cut.
    :type sprite: pygame.Surface
    :param cut_angle: direction of the cut line in radians.
    :type cut_angle: float
    :return: two halves with the unit normal pointing away from the cut for each.
    :rtype: list[tuple[pygame.Surface, tuple[float, float]]]
    """
    w, h = sprite.get_size()
    cx, cy = w / 2, h / 2
    big = w + h
    d = (math.cos(cut_angle), math.sin(cut_angle))
    n = (-d[1], d[0])
    halves = []
    for sign in (1.0, -1.0):
        poly = [
            (cx - d[0] * big, cy - d[1] * big), (cx + d[0] * big, cy + d[1] * big),
            (cx + d[0] * big + sign * n[0] * big, cy + d[1] * big + sign * n[1] * big),
            (cx - d[0] * big + sign * n[0] * big, cy - d[1] * big + sign * n[1] * big),
        ]
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255, 255, 255, 255), poly)
        half = sprite.copy()
        half.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        halves.append((half, (sign * n[0], sign * n[1])))
    return halves


class EffectsManager:
    """Owns and animates every transient visual effect."""

    def __init__(self, cfg: GameConfig, sprites: SpriteProvider, fonts: FontCache) -> None:
        """Create manager.

        :param cfg: game configuration.
        :type cfg: fruit_knight.config.schema.GameConfig
        :param sprites: sprite provider.
        :type sprites: fruit_knight.rendering.sprites.SpriteProvider
        :param fonts: font cache.
        :type fonts: fruit_knight.rendering.fonts.FontCache
        """
        self.cfg = cfg
        self.sprites = sprites
        self.fonts = fonts
        self._rng = random.Random()
        self._halves: list[_Half] = []
        self._particles: list[_Particle] = []
        self._popups: list[_Popup] = []
        self._rings: list[_Ring] = []
        self._trails: dict[str, deque[tuple[float, Vec]]] = {}
        self._trail_colors: dict[str, Color] = {}
        self._flash = 0.0

    # ------------------------------------------------------------------ input
    def player_color(self, player_id: int | None) -> Color:
        """Resolve a player's colour.

        :param player_id: player id, ``None`` for neutral white.
        :type player_id: int | None
        :return: RGB colour.
        :rtype: tuple[int, int, int]
        """
        if player_id is None:
            return (255, 255, 255)
        return tuple(self.cfg.players.colors[(player_id - 1) % len(self.cfg.players.colors)])  # type: ignore[return-value]

    def handle(self, event: GameEvent) -> None:
        """Turn a game event into visual effects.

        :param event: event emitted by the active mode.
        :type event: fruit_knight.modes.events.GameEvent
        """
        color = self.player_color(event.player_id)
        if event.kind == "slice":
            self._spawn_slice(event)
        elif event.kind == "explosion":
            self._spawn_explosion(event.pos, event.data.get("radius", 34.0))
        elif event.kind == "popup":
            bad = event.data.get("bad", False)
            self._popups.append(_Popup(event.text, list(event.pos), (255, 90, 90) if bad else color, self.cfg.ui.popup_lifetime_s, 34 if bad else 28))
        elif event.kind in ("defuse", "thrower_success", "goal"):
            self._popups.append(_Popup(event.text, list(event.pos), color, self.cfg.ui.popup_lifetime_s * 1.4, 44))
            self._rings.append(_Ring(event.pos, 120.0, color, 0.6, 0.6))
            self._burst(event.pos, color, 26, 380.0)
        elif event.kind == "eliminated":
            self._popups.append(_Popup(f"PLAYER {event.player_id} ELIMINATED", list(event.pos), color, 2.0, 48))
        elif event.kind == "grab":
            self._rings.append(_Ring(event.pos, 50.0, color, 0.25, 0.25))

    def _spawn_slice(self, event: GameEvent) -> None:
        """Create halves, juice and a flash for a sliced fruit.

        :param event: slice event with subtype, angle and velocity.
        :type event: fruit_knight.modes.events.GameEvent
        """
        data = event.data
        sprite = self.sprites.fruit(data["subtype"])
        vx, vy = data.get("velocity", (0.0, 0.0))
        for half, normal in split_sprite(sprite, data.get("angle", 0.0)):
            self._halves.append(_Half(
                half, [event.pos[0], event.pos[1]],
                [vx * 0.6 + normal[0] * HALF_SEPARATION_SPEED, vy * 0.6 + normal[1] * HALF_SEPARATION_SPEED - 80.0],
                data.get("spin", 0.0), self._rng.uniform(-220, 220), HALF_LIFETIME,
            ))
        self._burst(event.pos, tuple(self.cfg.fruits.subtypes[data["subtype"]].color), 14, 320.0)  # type: ignore[arg-type]
        self._rings.append(_Ring(event.pos, data.get("radius", 30.0) * 1.8, (255, 255, 255), 0.18, 0.18))

    def _spawn_explosion(self, pos: Vec, radius: float) -> None:
        """Create a bomb or grenade blast.

        :param pos: blast centre.
        :type pos: tuple[float, float]
        :param radius: source entity radius in pixels.
        :type radius: float
        """
        self._rings.append(_Ring(pos, radius * 5, (255, 170, 40), 0.5, 0.5))
        self._rings.append(_Ring(pos, radius * 3, (255, 240, 180), 0.3, 0.3))
        self._burst(pos, (255, 140, 30), 40, 560.0)
        self._flash = 0.25

    def _burst(self, pos: Vec, color: Color, count: int, speed: float) -> None:
        """Emit radial particles.

        :param pos: emission centre.
        :type pos: tuple[float, float]
        :param color: particle colour.
        :type color: tuple[int, int, int]
        :param count: number of particles.
        :type count: int
        :param speed: maximum particle speed in pixels per second.
        :type speed: float
        """
        for _ in range(count):
            a, s = self._rng.uniform(0, math.tau), self._rng.uniform(0.25, 1.0) * speed
            life = self._rng.uniform(0.3, 0.8)
            self._particles.append(_Particle([pos[0], pos[1]], [math.cos(a) * s, math.sin(a) * s], color, life, life, self._rng.uniform(2.5, 6.0)))

    # --------------------------------------------------------------- hands
    def track_hands(self, samples: dict[str, HandSample], now: float) -> None:
        """Record fingertip paths of knife hands for the slice trail.

        :param samples: current hand samples.
        :type samples: dict[str, fruit_knight.vision.hands.HandSample]
        :param now: current time in seconds.
        :type now: float
        """
        for key, s in samples.items():
            trail = self._trails.setdefault(key, deque(maxlen=self.cfg.ui.trail_length))
            self._trail_colors[key] = self.player_color(s.player_id)
            if s.state == HandState.KNIFE_HAND:
                trail.append((now, s.tip))

    # -------------------------------------------------------------- update
    def update(self, dt: float) -> None:
        """Advance animations.

        :param dt: time step in seconds.
        :type dt: float
        """
        for h in self._halves:
            h.vel[1] += HALF_GRAVITY * dt
            h.pos[0] += h.vel[0] * dt
            h.pos[1] += h.vel[1] * dt
            h.angle += h.spin * dt
            h.life -= dt
        for p in self._particles:
            p.vel[1] += PARTICLE_GRAVITY * dt
            p.pos[0] += p.vel[0] * dt
            p.pos[1] += p.vel[1] * dt
            p.life -= dt
        for pop in self._popups:
            pop.pos[1] -= 50 * dt
            pop.life -= dt
        for ring in self._rings:
            ring.life -= dt
        self._halves = [h for h in self._halves if h.life > 0]
        self._particles = [p for p in self._particles if p.life > 0]
        self._popups = [p for p in self._popups if p.life > 0]
        self._rings = [r for r in self._rings if r.life > 0]
        self._flash = max(0.0, self._flash - dt)

    def clear(self) -> None:
        """Drop every active effect."""
        self._halves.clear()
        self._particles.clear()
        self._popups.clear()
        self._rings.clear()
        self._trails.clear()

    # ---------------------------------------------------------------- draw
    def draw(self, surface: pygame.Surface, now: float) -> None:
        """Render all effects.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param now: current time in seconds (trail fading).
        :type now: float
        """
        self._draw_trails(surface, now)
        for h in self._halves:
            img = pygame.transform.rotate(h.surface, -math.degrees(h.angle))
            img.set_alpha(int(255 * min(1.0, h.life / 0.5)))
            surface.blit(img, img.get_rect(center=(int(h.pos[0]), int(h.pos[1]))))
        for ring in self._rings:
            t = 1 - ring.life / ring.max_life
            alpha_circle(surface, ring.color, int(200 * (1 - t)), ring.pos, max(2, ring.max_radius * t), 4)
        for p in self._particles:
            alpha_circle(surface, p.color, int(255 * p.life / p.max_life), (p.pos[0], p.pos[1]), p.radius)
        for pop in self._popups:
            img = self.fonts.text(pop.text, pop.size, pop.color, True)
            img.set_alpha(int(255 * min(1.0, pop.life / 0.4)))
            surface.blit(img, img.get_rect(center=(int(pop.pos[0]), int(pop.pos[1]))))
        if self._flash > 0:
            flash = pygame.Surface(surface.get_size())
            flash.fill((255, 220, 160))
            flash.set_alpha(int(110 * self._flash / 0.25))
            surface.blit(flash, (0, 0))

    def _draw_trails(self, surface: pygame.Surface, now: float) -> None:
        """Render fading slice trails.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param now: current time in seconds.
        :type now: float
        """
        life = self.cfg.ui.trail_lifetime_s
        for key, trail in self._trails.items():
            while trail and now - trail[0][0] > life:
                trail.popleft()
            color = self._trail_colors.get(key, (255, 255, 255))
            points = list(trail)
            for i in range(1, len(points)):
                age = (now - points[i][0]) / life
                width = max(2, int(14 * (1 - age) * i / len(points)) + 2)
                alpha_line(surface, color, int(230 * (1 - age)), points[i - 1][1], points[i][1], width)
