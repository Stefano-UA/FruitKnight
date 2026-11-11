"""Per-player match state and scoring."""

from __future__ import annotations

import math
from dataclasses import dataclass

from fruit_knight.config.schema import ScoringConfig


@dataclass
class PlayerState:
    """Mutable statistics of one player."""

    player_id: int
    lives: int
    max_lives: int
    eliminated: bool = False
    survival_time: float = 0.0
    fruits_sliced: int = 0
    fruit_points: int = 0
    holders_defused: int = 0
    throwers_completed: int = 0
    goals_scored: int = 0
    goals_conceded: int = 0
    bombs_hit: int = 0
    penalty_points: int = 0

    def score(self, scoring: ScoringConfig) -> int:
        """Compute total score.

        ``Score = fruit points + holders * P_holder + throwers * P_thrower
        + floor(t_survived * M_time) + goals * P_goal - penalty points``.

        :param scoring: scoring weights.
        :type scoring: fruit_knight.config.schema.ScoringConfig
        :return: total score.
        :rtype: int
        """
        return (
            self.fruit_points
            + self.holders_defused * scoring.holder_points
            + self.throwers_completed * scoring.thrower_points
            + math.floor(self.survival_time * scoring.time_multiplier)
            + self.goals_scored * scoring.football_goal_points
            - self.penalty_points
        )


@dataclass
class Standing:
    """Final ranking row of a player."""

    rank: int
    player: PlayerState
    score: int
    winner: bool
