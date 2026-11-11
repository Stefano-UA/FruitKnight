"""YAML loading, typed conversion and validation of the game configuration."""

from __future__ import annotations

import dataclasses
import typing
from pathlib import Path
from typing import Any

import yaml

from fruit_knight.config.schema import GameConfig
from fruit_knight.utils.paths import resource_path


class ConfigError(ValueError):
    """Raised when ``settings.yaml`` is malformed or inconsistent."""


def _convert(value: Any, hint: Any, path: str) -> Any:
    """Convert raw YAML data into the type described by a type hint.

    :param value: raw YAML value.
    :type value: typing.Any
    :param hint: resolved type annotation.
    :type hint: typing.Any
    :param path: dotted location used in error messages.
    :type path: str
    :return: value converted to ``hint``.
    :rtype: typing.Any
    """
    origin = typing.get_origin(hint)
    args = typing.get_args(hint)
    if dataclasses.is_dataclass(hint):
        if not isinstance(value, dict):
            raise ConfigError(f"'{path}' must be a mapping")
        return _build(hint, value, path)
    if origin is dict:
        if not isinstance(value, dict):
            raise ConfigError(f"'{path}' must be a mapping")
        return {str(k): _convert(v, args[1], f"{path}.{k}") for k, v in value.items()}
    if origin is list:
        if not isinstance(value, (list, tuple)):
            raise ConfigError(f"'{path}' must be a list")
        return [_convert(v, args[0], f"{path}[{i}]") for i, v in enumerate(value)]
    if origin is tuple:
        if not isinstance(value, (list, tuple)):
            raise ConfigError(f"'{path}' must be a list of {len(args)} items")
        if len(value) != len(args):
            raise ConfigError(f"'{path}' needs {len(args)} items, got {len(value)}")
        return tuple(_convert(v, a, f"{path}[{i}]") for i, (v, a) in enumerate(zip(value, args)))
    try:
        if hint is bool:
            if not isinstance(value, bool):
                raise TypeError
            return value
        if hint in (int, float, str):
            return hint(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"'{path}' must be {hint.__name__}, got {value!r}") from exc
    return value


def _build(cls: type, data: dict[str, Any], path: str) -> Any:
    """Instantiate a dataclass from a mapping, rejecting unknown keys.

    :param cls: target dataclass type.
    :type cls: type
    :param data: raw mapping from YAML.
    :type data: dict[str, typing.Any]
    :param path: dotted location used in error messages.
    :type path: str
    :return: populated dataclass instance.
    :rtype: typing.Any
    """
    hints = typing.get_type_hints(cls)
    unknown = set(data) - set(hints)
    if unknown:
        raise ConfigError(f"Unknown keys in '{path or 'root'}': {sorted(unknown)}")
    kwargs = {name: _convert(val, hints[name], f"{path}.{name}".lstrip(".")) for name, val in data.items()}
    return cls(**kwargs)


def _check_range(name: str, bounds: tuple[float, float], low: float = 0.0) -> None:
    """Validate an ordered, bounded range.

    :param name: setting name used in error messages.
    :type name: str
    :param bounds: ``(min, max)`` pair.
    :type bounds: tuple[float, float]
    :param low: smallest allowed value.
    :type low: float
    """
    if bounds[0] > bounds[1] or bounds[0] < low:
        raise ConfigError(f"'{name}' must satisfy {low} <= min <= max, got {bounds}")


def validate(cfg: GameConfig) -> None:
    """Check semantic constraints of a loaded configuration.

    :param cfg: configuration to verify.
    :type cfg: fruit_knight.config.schema.GameConfig
    :raises ConfigError: when a value is out of bounds.
    """
    if cfg.window.width < 640 or cfg.window.height < 360:
        raise ConfigError("window must be at least 640x360")
    if cfg.physics.gravity <= 0 or cfg.physics.substeps < 1:
        raise ConfigError("physics.gravity must be > 0 and physics.substeps >= 1")
    if cfg.countdown_seconds < 0:
        raise ConfigError("countdown_seconds must be >= 0")
    if len(cfg.players.colors) < 4 or len(cfg.players.names) < 4:
        raise ConfigError("players.colors and players.names need 4 entries")
    if not cfg.fruits.subtypes:
        raise ConfigError("at least one fruit subtype is required")
    for name, sub in cfg.fruits.subtypes.items():
        if sub.weight <= 0 or sub.radius <= 0 or sub.spawn_weight <= 0:
            raise ConfigError(f"fruit '{name}' needs positive weight, radius and spawn_weight")
    launches = {
        "fruits.launch": cfg.fruits.launch, "bomb.launch": cfg.bomb.launch,
        "holder.launch": cfg.holder.launch, "thrower.launch": cfg.thrower.launch,
    }
    for name, launch in launches.items():
        _check_range(f"{name}.height_ratio", (launch.min_height_ratio, launch.max_height_ratio))
        _check_range(f"{name}.angle_deg", (launch.min_angle_deg, launch.max_angle_deg))
        if launch.max_height_ratio > 1.5 or launch.max_angle_deg >= 80:
            raise ConfigError(f"'{name}' launches are out of sensible bounds")
    for name, rng in (
        ("spawning.jitter_range", cfg.spawning.jitter_range),
        ("bomb.initial_delay_range", cfg.bomb.initial_delay_range),
        ("bomb.interval_range", cfg.bomb.interval_range),
        ("limiter.initial_delay_range", cfg.limiter.initial_delay_range),
        ("limiter.interval_range", cfg.limiter.interval_range),
        ("limiter.lifetime_range", cfg.limiter.lifetime_range),
        ("holder.initial_delay_range", cfg.holder.initial_delay_range),
        ("holder.interval_range", cfg.holder.interval_range),
        ("holder.hold_duration_range", cfg.holder.hold_duration_range),
        ("thrower.initial_delay_range", cfg.thrower.initial_delay_range),
        ("thrower.interval_range", cfg.thrower.interval_range),
        ("thrower.expiration_range", cfg.thrower.expiration_range),
    ):
        _check_range(name, rng)
    if not 0.0 < cfg.football.goal_bottom_edge_ratio < 0.5:
        raise ConfigError("football.goal_bottom_edge_ratio must be in (0, 0.5)")
    if cfg.spawning.min_spawn_interval <= 0 or not 0.0 <= cfg.spawning.spawn_margin_ratio < 0.4:
        raise ConfigError("spawning.min_spawn_interval > 0 and spawn_margin_ratio in [0, 0.4)")
    if cfg.gestures.debounce_frames < 1 or not 0.0 < cfg.gestures.velocity_smoothing <= 1.0:
        raise ConfigError("gestures.debounce_frames >= 1 and velocity_smoothing in (0, 1]")
    if cfg.defaults.mode not in {"1p_endurance", "np_endurance", "np_competition", "2p_football"}:
        raise ConfigError(f"unknown defaults.mode '{cfg.defaults.mode}'")
    if cfg.tracking.default_mode not in {"pose_hands", "hands_only"}:
        raise ConfigError(f"unknown tracking.default_mode '{cfg.tracking.default_mode}'")


def load_config(path: str | Path | None = None) -> GameConfig:
    """Load and validate ``settings.yaml``.

    :param path: YAML file location; bundled ``config/settings.yaml`` when omitted.
    :type path: str | pathlib.Path | None
    :return: validated typed configuration.
    :rtype: fruit_knight.config.schema.GameConfig
    :raises ConfigError: when the file is malformed or inconsistent.
    """
    target = Path(path) if path else resource_path("config", "settings.yaml")
    try:
        with open(target, "r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Cannot read configuration '{target}': {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("configuration root must be a mapping")
    cfg = _build(GameConfig, raw, "")
    validate(cfg)
    return cfg
