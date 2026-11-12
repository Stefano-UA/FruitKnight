"""Configuration loading and typed schemas."""

from fruit_knight.config.loader import ConfigError, apply_difficulty, load_config, validate
from fruit_knight.config.schema import GameConfig

__all__ = ["ConfigError", "GameConfig", "apply_difficulty", "load_config", "validate"]
