"""Timed competition mode."""

from __future__ import annotations

import random

from fruit_knight.config.schema import GameConfig
from fruit_knight.modes.base import BaseGameMode
from fruit_knight.modes.players import PlayerState
from fruit_knight.modes.setup import MatchSetup
from fruit_knight.utils.constants import ModeId, PenaltyReason
from fruit_knight.utils.timers import Timer


class CompetitionMode(BaseGameMode):
    """Fixed-duration match; highest score wins when the clock reaches zero."""

    mode_id = ModeId.COMPETITION_NP

    def __init__(self, cfg: GameConfig, setup: MatchSetup, size: tuple[int, int], rng: random.Random | None = None) -> None:
        """Create match with its countdown clock.

        :param cfg: game configuration.
        :type cfg: fruit_knight.config.schema.GameConfig
        :param setup: match options (``timespan`` and ``competition_penalty``).
        :type setup: fruit_knight.modes.setup.MatchSetup
        :param size: screen width and height in pixels.
        :type size: tuple[int, int]
        :param rng: random generator.
        :type rng: random.Random | None
        """
        super().__init__(cfg, setup, size, rng)
        self.clock = Timer(float(setup.timespan))

    @property
    def points_penalties(self) -> bool:
        """Report whether penalties cost points instead of lives.

        :return: True for the ``points`` penalty option.
        :rtype: bool
        """
        return self.setup.competition_penalty == "points"

    @property
    def time_left(self) -> float | None:
        """Report remaining match time.

        :return: seconds left.
        :rtype: float | None
        """
        return self.clock.remaining

    def apply_penalty_effect(self, player: PlayerState, reason: PenaltyReason, instant: bool) -> None:
        """Deduct points or lives depending on the setup.

        :param player: penalised player.
        :type player: fruit_knight.modes.players.PlayerState
        :param reason: penalty cause.
        :type reason: fruit_knight.utils.constants.PenaltyReason
        :param instant: True when the cause kills instantly (ignored in points mode).
        :type instant: bool
        """
        if self.points_penalties:
            player.penalty_points += self.cfg.scoring.penalty_points_loss
        else:
            super().apply_penalty_effect(player, reason, instant)

    def on_tick(self, dt: float) -> None:
        """Advance the countdown.

        :param dt: time step in seconds.
        :type dt: float
        """
        self.clock.update(dt)

    def check_finished(self) -> bool:
        """End when the clock expires or everybody is eliminated.

        :return: True when the match is over.
        :rtype: bool
        """
        return self.clock.done or super().check_finished()
