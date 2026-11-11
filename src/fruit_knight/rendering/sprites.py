"""Resolves every configured sprite path to a surface (file or procedural fallback)."""

from __future__ import annotations

import pygame

from fruit_knight.config.schema import GameConfig
from fruit_knight.rendering import procedural
from fruit_knight.rendering.assets import AssetManager

Size = tuple[int, int]


class SpriteProvider:
    """Facade over ``AssetManager`` binding config paths to procedural painters."""

    def __init__(self, cfg: GameConfig, assets: AssetManager) -> None:
        """Create provider.

        :param cfg: game configuration with sprite paths.
        :type cfg: fruit_knight.config.schema.GameConfig
        :param assets: asset manager.
        :type assets: fruit_knight.rendering.assets.AssetManager
        """
        self.cfg = cfg
        self.assets = assets

    def fruit(self, subtype: str) -> pygame.Surface:
        """Fetch fruit sprite.

        :param subtype: fruit subtype key.
        :type subtype: str
        :return: sprite sized to the fruit diameter.
        :rtype: pygame.Surface
        """
        spec = self.cfg.fruits.subtypes[subtype]
        d = int(spec.radius * 2)
        return self.assets.get(spec.sprite_path, (d, d), lambda s: procedural.paint_fruit(subtype, spec.color, s), subtype)

    def bomb(self) -> pygame.Surface:
        """Fetch bomb sprite.

        :return: sprite sized to the bomb diameter.
        :rtype: pygame.Surface
        """
        c = self.cfg.bomb
        d = int(c.radius * 2)
        return self.assets.get(c.sprite_path, (d, d), lambda s: procedural.paint_bomb(c.color, s))

    def holder(self, defused: bool) -> pygame.Surface:
        """Fetch holder sprite.

        :param defused: return the defused variant.
        :type defused: bool
        :return: sprite sized to the holder diameter.
        :rtype: pygame.Surface
        """
        c = self.cfg.holder
        d = int(c.radius * 2)
        path = c.defused_sprite_path if defused else c.active_sprite_path
        color = c.defused_color if defused else c.active_color
        return self.assets.get(path, (d, d), lambda s: procedural.paint_holder(color, s, defused), "defused" if defused else "active")

    def thrower(self) -> pygame.Surface:
        """Fetch thrower sprite.

        :return: sprite sized to the thrower diameter.
        :rtype: pygame.Surface
        """
        c = self.cfg.thrower
        d = int(c.radius * 2)
        return self.assets.get(c.sprite_path, (d, d), lambda s: procedural.paint_thrower(c.color, s))

    def limiter_texture(self, variant: str, size: Size) -> pygame.Surface:
        """Fetch limiter texture (tip at the right end).

        :param variant: ``"trunk"`` or ``"beam"``.
        :type variant: str
        :param size: texture length and thickness.
        :type size: tuple[int, int]
        :return: texture surface.
        :rtype: pygame.Surface
        """
        c = self.cfg.limiter
        path = c.sprite_path if variant == "trunk" else c.beam_sprite_path
        return self.assets.get(path, size, lambda s: procedural.paint_limiter(variant, s), variant)

    def portal(self, size: Size, color: tuple[int, int, int]) -> pygame.Surface:
        """Fetch target-zone sprite.

        :param size: zone size in pixels.
        :type size: tuple[int, int]
        :param color: accent colour for the fallback.
        :type color: tuple[int, int, int]
        :return: portal surface.
        :rtype: pygame.Surface
        """
        return self.assets.get(self.cfg.thrower.zone_sprite_path, size, lambda s: procedural.paint_portal(color, s), str(color))

    def heart(self, filled: bool, size: int = 30) -> pygame.Surface:
        """Fetch life icon.

        :param filled: return the filled heart.
        :type filled: bool
        :param size: icon size in pixels.
        :type size: int
        :return: heart surface.
        :rtype: pygame.Surface
        """
        path = self.cfg.ui.heart_sprite_path
        sprite = self.assets.get(path, (size, size), lambda s: procedural.paint_heart(s, filled), "full" if filled else "empty")
        if filled or not self.assets.exists(path):
            return sprite
        dim = sprite.copy()  # a real heart sprite is greyed out for lost lives
        dim.fill((90, 90, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
        return dim

    def background(self, size: Size) -> pygame.Surface:
        """Fetch menu / no-camera background.

        :param size: surface size in pixels.
        :type size: tuple[int, int]
        :return: background surface.
        :rtype: pygame.Surface
        """
        return self.assets.get(self.cfg.ui.background_sprite_path, size, procedural.paint_background)

    def logo(self, size: Size) -> pygame.Surface:
        """Fetch title logo.

        :param size: logo size in pixels.
        :type size: tuple[int, int]
        :return: logo surface.
        :rtype: pygame.Surface
        """
        return self.assets.get(self.cfg.ui.logo_sprite_path, size, procedural.paint_logo)

    def all_configured_paths(self) -> list[str]:
        """List every sprite path referenced by the configuration.

        :return: sprite paths relative to the repository root.
        :rtype: list[str]
        """
        c = self.cfg
        paths = [s.sprite_path for s in c.fruits.subtypes.values()]
        paths += [
            c.bomb.sprite_path, c.limiter.sprite_path, c.limiter.beam_sprite_path,
            c.holder.active_sprite_path, c.holder.defused_sprite_path,
            c.thrower.sprite_path, c.thrower.zone_sprite_path,
            c.ui.heart_sprite_path, c.ui.background_sprite_path, c.ui.logo_sprite_path,
        ]
        return [p for p in paths if p]
