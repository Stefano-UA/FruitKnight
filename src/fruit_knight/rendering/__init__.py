"""Rendering: asset manager with procedural fallbacks, overlays, effects and entity drawing."""

from fruit_knight.rendering.assets import AssetManager
from fruit_knight.rendering.effects import EffectsManager
from fruit_knight.rendering.entity_renderer import EntityRenderer
from fruit_knight.rendering.fonts import FontCache
from fruit_knight.rendering.sprites import SpriteProvider

__all__ = ["AssetManager", "EffectsManager", "EntityRenderer", "FontCache", "SpriteProvider"]
