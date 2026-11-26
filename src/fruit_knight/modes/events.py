"""Game events emitted by modes for the presentation layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Vec = tuple[float, float]


@dataclass
class GameEvent:
    """Something visible that happened during a tick.

    Kinds: ``slice``, ``explosion``, ``popup``, ``defuse``, ``goal``, ``grab``, ``release``,
    ``eliminated``, ``thrower_success``.
    """

    kind: str
    pos: Vec
    player_id: int | None = None
    text: str = ""
    data: dict[str, Any] = field(default_factory=dict)
