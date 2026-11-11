"""Draws entities of a running mode."""

from __future__ import annotations

import math

import pygame

from fruit_knight.entities import BarrierLimiter, Bomb, Fruit, Holder, HolderState, Projectile, TargetZone, Thrower
from fruit_knight.modes.base import BaseGameMode
from fruit_knight.rendering.draw_utils import alpha_circle, alpha_rect, arc_points
from fruit_knight.rendering.fonts import FontCache
from fruit_knight.rendering.sprites import SpriteProvider

Color = tuple[int, int, int]
# Visual-only constants.
HALO_PADDING = 7
BADGE_RADIUS = 13


class EntityRenderer:
    """Renders fruits, bombs, grenades, limiters and target zones."""

    def __init__(self, sprites: SpriteProvider, fonts: FontCache) -> None:
        """Create renderer.

        :param sprites: sprite provider.
        :type sprites: fruit_knight.rendering.sprites.SpriteProvider
        :param fonts: font cache.
        :type fonts: fruit_knight.rendering.fonts.FontCache
        """
        self.sprites = sprites
        self.fonts = fonts
        self.cfg = sprites.cfg

    def _color(self, player_id: int | None) -> Color:
        """Resolve a player's colour.

        :param player_id: player id.
        :type player_id: int | None
        :return: RGB colour.
        :rtype: tuple[int, int, int]
        """
        colors = self.cfg.players.colors
        return tuple(colors[((player_id or 1) - 1) % len(colors)])  # type: ignore[return-value]

    def draw(self, surface: pygame.Surface, mode: BaseGameMode, now: float) -> None:
        """Draw every entity, back to front.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param mode: running mode providing entities.
        :type mode: fruit_knight.modes.base.BaseGameMode
        :param now: wall-clock time in seconds for animations.
        :type now: float
        """
        multi = len(mode.players) > 1
        ordered = sorted(mode.entities, key=lambda e: (not isinstance(e, TargetZone), not isinstance(e, BarrierLimiter)))
        for entity in ordered:
            if not entity.alive:
                continue
            if isinstance(entity, TargetZone):
                self._draw_zone(surface, entity, now, multi)
            elif isinstance(entity, BarrierLimiter):
                self._draw_limiter(surface, entity, now)
            elif isinstance(entity, Projectile):
                self._draw_projectile(surface, entity, now, multi)

    # ----------------------------------------------------------- projectiles
    def _sprite_for(self, entity: Projectile) -> pygame.Surface:
        """Select the sprite of a projectile.

        :param entity: projectile to draw.
        :type entity: fruit_knight.entities.base.Projectile
        :return: sprite surface.
        :rtype: pygame.Surface
        """
        if isinstance(entity, Fruit):
            return self.sprites.fruit(entity.subtype)
        if isinstance(entity, Bomb):
            return self.sprites.bomb()
        if isinstance(entity, Holder):
            return self.sprites.holder(entity.state == HolderState.DEFUSED)
        return self.sprites.thrower()

    def _draw_projectile(self, surface: pygame.Surface, entity: Projectile, now: float, multi: bool) -> None:
        """Draw one projectile with halo, rotation and status decorations.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param entity: projectile to draw.
        :type entity: fruit_knight.entities.base.Projectile
        :param now: wall-clock time in seconds.
        :type now: float
        :param multi: True when several players play, enabling halos and badges.
        :type multi: bool
        """
        x, y = entity.position
        assert entity.body is not None
        if multi and entity.target_player is not None:
            alpha_circle(surface, self._color(entity.target_player), 150, (x, y), entity.radius + HALO_PADDING, 4)
        sprite = self.sprites.assets.rotated(self._sprite_for(entity), -math.degrees(entity.body.angle))
        surface.blit(sprite, sprite.get_rect(center=(int(x), int(y))))
        if entity.held_by is not None:
            alpha_circle(surface, (255, 255, 255), 200, (x, y), entity.radius + 5, 3)
        if isinstance(entity, Holder):
            self._draw_holder_status(surface, entity, now)
        elif isinstance(entity, Thrower):
            self._draw_thrower_status(surface, entity)
        if multi and isinstance(entity, (Holder, Thrower)) and entity.target_player is not None:
            bx, by = int(x + entity.radius * 0.8), int(y - entity.radius * 0.8)
            pygame.draw.circle(surface, self._color(entity.target_player), (bx, by), BADGE_RADIUS)
            pygame.draw.circle(surface, (255, 255, 255), (bx, by), BADGE_RADIUS, 2)
            self.fonts.draw_centered(surface, str(entity.target_player), 18, (10, 10, 20), (bx, by), shadow=False)

    def _draw_holder_status(self, surface: pygame.Surface, holder: Holder, now: float) -> None:
        """Draw radial remaining-hold progress around a holder.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param holder: holder to decorate.
        :type holder: fruit_knight.entities.holder.Holder
        :param now: wall-clock time in seconds for the pulse.
        :type now: float
        """
        c = holder.position
        r = holder.radius + 11
        pygame.draw.circle(surface, (30, 34, 52), c, r, 6)
        if holder.state == HolderState.DEFUSED:
            pygame.draw.circle(surface, self.cfg.holder.defused_color, c, r, 6)
            return
        if holder.progress > 0.002:
            pts = arc_points(c, r, -math.pi / 2, math.tau * holder.progress, 48)
            pygame.draw.lines(surface, (255, 235, 59), False, pts, 6)
        if holder.held_by is not None:
            self.fonts.draw_centered(surface, f"{holder.remaining:0.1f}s", 20, (255, 255, 255), (c[0], c[1] + r + 18))
        else:
            pulse = 0.5 + 0.5 * math.sin(now * 6)
            self.fonts.draw_centered(surface, "GRAB & HOLD", 16, (255, int(180 + 60 * pulse), 100), (c[0], c[1] + r + 16))

    def _draw_thrower_status(self, surface: pygame.Surface, thrower: Thrower) -> None:
        """Draw expiry arc around a thrower.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param thrower: thrower to decorate.
        :type thrower: fruit_knight.entities.thrower.Thrower
        """
        c, r = thrower.position, thrower.radius + 10
        left = 1.0 - thrower.expiry.progress
        pts = arc_points(c, r, -math.pi / 2, math.tau * left, 48)
        color = (255, int(80 + 175 * left), 80)
        if left > 0.01:
            pygame.draw.lines(surface, color, False, pts, 4)

    # ------------------------------------------------------------- limiter
    def _draw_limiter(self, surface: pygame.Surface, limiter: BarrierLimiter, now: float) -> None:
        """Draw a limiter, its tip hitbox hint and state.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param limiter: limiter to draw.
        :type limiter: fruit_knight.entities.limiter.BarrierLimiter
        :param now: wall-clock time in seconds for the pulse.
        :type now: float
        """
        thick = int(limiter.cfg.thickness)
        full = int(limiter.world.width * 1.15)
        length = max(2, int(limiter.length))
        texture = self.sprites.limiter_texture(limiter.variant, (full, thick))
        part = texture.subsurface(pygame.Rect(max(0, full - length), 0, min(length, full), thick))
        image = pygame.transform.rotate(part, -math.degrees(limiter.angle))
        ox, oy = limiter.origin
        dx, dy = limiter.direction
        center = (ox + dx * length / 2, oy + dy * length / 2)
        surface.blit(image, image.get_rect(center=(int(center[0]), int(center[1]))))
        if limiter.retracting:
            return
        tip = limiter.tip
        pulse = 0.5 + 0.5 * math.sin(now * 7)
        if limiter.stopped:
            alpha_circle(surface, (102, 187, 106), 200, tip, limiter.cfg.tip_hit_radius, 5)
            self.fonts.draw_centered(surface, "HOLDING", 18, (102, 187, 106), (tip[0], tip[1] - limiter.cfg.tip_hit_radius - 14))
        else:
            alpha_circle(surface, (255, 235, 59), int(90 + 110 * pulse), tip, limiter.cfg.tip_hit_radius, 4)
            self.fonts.draw_centered(surface, "OPEN PALM HERE", 16, (255, 235, 59), (tip[0], tip[1] - limiter.cfg.tip_hit_radius - 14))

    # ---------------------------------------------------------------- zone
    def _draw_zone(self, surface: pygame.Surface, zone: TargetZone, now: float, multi: bool) -> None:
        """Draw an animated target zone with direction chevrons.

        :param surface: target surface.
        :type surface: pygame.Surface
        :param zone: zone to draw.
        :type zone: fruit_knight.entities.target_zone.TargetZone
        :param now: wall-clock time in seconds for the animation.
        :type now: float
        :param multi: True when several players play.
        :type multi: bool
        """
        x, y, w, h = zone.rect
        color = self._color(zone.player_id) if zone.player_id else tuple(self.cfg.thrower.color)
        sprite = self.sprites.portal((int(w), int(h)), color)  # type: ignore[arg-type]
        surface.blit(sprite, (int(x), int(y)))
        pulse = 0.5 + 0.5 * math.sin(now * 5)
        alpha_rect(surface, color, int(40 + 50 * pulse), pygame.Rect(int(x), int(y), int(w), int(h)), 18)  # type: ignore[arg-type]
        # Chevrons slide toward the margin the zone belongs to.
        step = ((now * 60) % 40) / 40
        vertical = zone.side == "top"
        for k in range(3):
            t = (k + step) / 3
            if vertical:
                cx, cy = x + w / 2, y + h * (1 - t)
                pts = [(cx - 22, cy + 10), (cx, cy - 10), (cx + 22, cy + 10)]
            else:
                direction = -1 if zone.side == "left" else 1
                cx = x + w / 2 + direction * (t - 0.5) * w * 0.8
                cy = y + h / 2
                pts = [(cx - direction * 10, cy - 22), (cx + direction * 10, cy), (cx - direction * 10, cy + 22)]
            pygame.draw.lines(surface, (255, 255, 255), False, pts, 5)
        label = f"TARGET P{zone.player_id}" if multi and zone.player_id else "TARGET"
        self.fonts.draw_centered(surface, label, 20, color, (x + w / 2, y + h / 2 + (28 if vertical else -h * 0.5 + 18)))  # type: ignore[arg-type]
