"""Configuration loading and typed schemas."""

from fruit_knight.config.loader import ConfigError, load_config, validate
from fruit_knight.config.schema import GameConfig

__all__ = ["ConfigError", "GameConfig", "load_config", "validate"]
