"""2P Football / Versus mode: throw fruits into the opponent's goal."""

from __future__ import annotations

import random

from fruit_knight.config.schema import GameConfig
from fruit_knight.entities import Fruit, Projectile
from fruit_knight.modes.base import BaseGameMode
from fruit_knight.modes.events import GameEvent
from fruit_knight.modes.setup import MatchSetup
from fruit_knight.utils.constants import ModeId, PenaltyReason
from fruit_knight.utils.timers import Timer


class FootballMode(BaseGameMode):
    """Player 1 defends the left goal, Player 2 the right goal."""

    mode_id = ModeId.FOOTBALL_2P
    limiter_allowed = False

    def __init__(self, cfg: GameConfig, setup: MatchSetup, size: tuple[int, int], rng: random.Random | None = None) -> None:
        """Create match with clock.

        :param cfg: game configuration.
        :type cfg: fruit_knight.config.schema.GameConfig
        :param setup: match options (exactly two players).
        :type setup: fruit_knight.modes.setup.MatchSetup
        :param size: screen width and height in pixels.
        :type size: tuple[int, int]
        :param rng: random generator.
        :type rng: random.Random | None
        """
        super().__init__(cfg, setup, size, rng)
        self.clock = Timer(float(setup.timespan))

    def spawn_lanes(self) -> list[int | None]:
        """Give each player an independent spawn lane on their half.

        :return: ``[1, 2]``.
        :rtype: list[int | None]
        """
        return [1, 2]

    @property
    def time_left(self) -> float | None:
        """Report remaining match time.

        :return: seconds left.
        :rtype: float | None
        """
        return self.clock.remaining

    def goal_owner(self, pos: tuple[float, float]) -> int | None:
        """Find whose defended goal zone contains a point.

        Left goal: left edge plus the bottom-left segment; right goal mirrors it.

        :param pos: entity centre in pixels.
        :type pos: tuple[float, float]
        :return: defending player id or ``None`` outside both goals.
        :rtype: int | None
        """
        w, h = self.size
        ratio = self.cfg.football.goal_bottom_edge_ratio
        x, y = pos
        if x <= 0 or (y >= h and x <= w * ratio):
            return 1
        if x >= w or (y >= h and x >= w * (1 - ratio)):
            return 2
        return None

    def on_entity_checked(self, entity: Projectile) -> bool:
        """Score a goal when a fruit thrown by the opponent enters a defended zone.

        :param entity: projectile being checked.
        :type entity: fruit_knight.entities.base.Projectile
        :return: True when a goal consumed the fruit.
        :rtype: bool
        """
        if not isinstance(entity, Fruit) or entity.sliced or entity.held_by is not None:
            return False
        defender = self.goal_owner(entity.position)
        if defender is None:
            return False
        attacker = 2 if defender == 1 else 1
        # Only fruits last thrown by the opponent count; own throws and spawns never score.
        if entity.last_thrower != attacker:
            return False
        scorer, victim = self.players[attacker], self.players[defender]
        scorer.goals_scored += 1
        victim.goals_conceded += 1
        pos = self._edge_point(entity.position)
        self.emit(GameEvent("goal", pos, attacker, f"GOAL! +{self.cfg.scoring.football_goal_points}", {"defender": defender}))
        entity.remove()
        self.penalize(defender, PenaltyReason.GOAL, pos)
        return True

    def on_fruit_exit(self, fruit: Fruit, side: str) -> None:
        """Ignore fruits leaving the screen: only goals cost lives in this mode.

        :param fruit: exiting fruit.
        :type fruit: fruit_knight.entities.fruit.Fruit
        :param side: exit side.
        :type side: str
        """

    def on_tick(self, dt: float) -> None:
        """Advance the match clock.

        :param dt: time step in seconds.
        :type dt: float
        """
        self.clock.update(dt)

    def check_finished(self) -> bool:
        """End when time is up or a player lost all lives.

        :return: True when the match is over.
        :rtype: bool
        """
        return self.clock.done or any(p.eliminated for p in self.players.values())
