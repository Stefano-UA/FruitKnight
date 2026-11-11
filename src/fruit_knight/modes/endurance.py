"""Endurance modes: survive as long as possible with independent lives."""

from __future__ import annotations

from fruit_knight.modes.base import BaseGameMode
from fruit_knight.utils.constants import ModeId


class MultiEnduranceMode(BaseGameMode):
    """N players with independent lives and scores; the match ends when all are eliminated."""

    mode_id = ModeId.ENDURANCE_NP

    def on_tick(self, dt: float) -> None:
        """Run per-frame logic (none beyond the base rules).

        :param dt: time step in seconds.
        :type dt: float
        """


class SoloEnduranceMode(MultiEnduranceMode):
    """Single-player endurance."""

    mode_id = ModeId.ENDURANCE_1P
