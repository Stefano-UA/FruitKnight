"""Time-driven spawning of fruits and hazards with dynamic difficulty."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from fruit_knight.config.schema import GameConfig
from fruit_knight.entities import BaseEntity, BarrierLimiter, EntityFactory, Holder, Thrower
from fruit_knight.modes.setup import MatchSetup
from fruit_knight.utils.math_utils import rand_range
from fruit_knight.utils.timers import ScheduledEvent

if TYPE_CHECKING:  # pragma: no cover
    from fruit_knight.modes.base import BaseGameMode

# Hazard intervals shrink with exp(rate * t * HAZARD_RATE_SHARE) so hazards tighten more slowly than fruit.
HAZARD_RATE_SHARE = 0.5
# Delay before a blocked hazard retries, in seconds.
RETRY_DELAY = 1.0


class Spawner:
    """Decides when and where entities appear."""

    def __init__(self, cfg: GameConfig, setup: MatchSetup, factory: EntityFactory, rng: random.Random, lanes: list[int | None], limiter_allowed: bool) -> None:
        """Create spawner and schedule initial dead-times.

        :param cfg: game configuration.
        :type cfg: fruit_knight.config.schema.GameConfig
        :param setup: match options.
        :type setup: fruit_knight.modes.setup.MatchSetup
        :param factory: entity factory.
        :type factory: fruit_knight.entities.factory.EntityFactory
        :param rng: random generator.
        :type rng: random.Random
        :param lanes: independent spawn lanes; player ids for versus modes, ``[None]`` otherwise.
        :type lanes: list[int | None]
        :param limiter_allowed: whether barrier limiters may spawn in this mode.
        :type limiter_allowed: bool
        """
        self.cfg, self.setup, self.factory, self.rng, self.lanes = cfg, setup, factory, rng, lanes
        self._next_fruit = {lane: rand_range(rng, cfg.spawning.fruit_initial_delay_range) for lane in lanes}
        self._bombs = {lane: ScheduledEvent(rng, cfg.bomb.initial_delay_range, cfg.bomb.interval_range) for lane in lanes}
        self._limiter = ScheduledEvent(rng, cfg.limiter.initial_delay_range, cfg.limiter.interval_range)
        self._holder = ScheduledEvent(rng, cfg.holder.initial_delay_range, cfg.holder.interval_range)
        self._thrower = ScheduledEvent(rng, cfg.thrower.initial_delay_range, cfg.thrower.interval_range)
        self._limiter_allowed = limiter_allowed

    # ------------------------------------------------------------------ rules
    def fruit_interval(self, t: float) -> float:
        """Compute fruit spawn interval at match time ``t``.

        :param t: match time in seconds.
        :type t: float
        :return: interval in seconds, never below ``min_spawn_interval``.
        :rtype: float
        """
        s = self.cfg.spawning
        base = max(s.min_spawn_interval, s.base_spawn_interval * math.exp(-s.spawn_acceleration_rate * t))
        return max(s.min_spawn_interval, base * rand_range(self.rng, s.jitter_range))

    def hazard_speedup(self, t: float) -> float:
        """Compute divisor shrinking hazard intervals over time.

        :param t: match time in seconds.
        :type t: float
        :return: speed-up factor ``>= 1``.
        :rtype: float
        """
        return math.exp(self.cfg.spawning.spawn_acceleration_rate * t * HAZARD_RATE_SHARE)

    def sector(self, player_id: int) -> tuple[float, float]:
        """Compute horizontal spawn band of a player.

        :param player_id: player id (1-based).
        :type player_id: int
        :return: left and right x coordinates in pixels.
        :rtype: tuple[float, float]
        """
        w = self.factory.world.width
        n = self.setup.players
        margin = w * self.cfg.spawning.spawn_margin_ratio
        lo, hi = w * (player_id - 1) / n, w * player_id / n
        lo = max(lo, margin) if player_id == 1 else lo + margin * 0.25
        hi = min(hi, w - margin) if player_id == n else hi - margin * 0.25
        return lo, max(lo + 1.0, hi)

    def _target(self, lane: int | None, alive: list[int]) -> int | None:
        """Choose target player for a spawn.

        :param lane: lane owner or ``None``.
        :type lane: int | None
        :param alive: ids of non-eliminated players.
        :type alive: list[int]
        :return: player id or ``None`` when nobody is alive.
        :rtype: int | None
        """
        if lane is not None:
            return lane
        return self.rng.choice(alive) if alive else None

    # ----------------------------------------------------------------- update
    def update(self, now: float, mode: "BaseGameMode") -> list[BaseEntity]:
        """Spawn everything that became due.

        :param now: match time in seconds.
        :type now: float
        :param mode: running mode, queried for alive players and live entities.
        :type mode: fruit_knight.modes.base.BaseGameMode
        :return: newly created entities.
        :rtype: list[fruit_knight.entities.base.BaseEntity]
        """
        alive = mode.alive_ids()
        out: list[BaseEntity] = []
        speedup = self.hazard_speedup(now)
        for lane in self.lanes:
            target = self._target(lane, alive)
            if target is None:
                continue
            lo, hi = self.sector(target)
            if now >= self._next_fruit[lane]:
                out.append(self.factory.fruit(self.rng.uniform(lo, hi), target))
                self._next_fruit[lane] = now + self.fruit_interval(now)
            bomb = self._bombs[lane]
            if self.setup.enable_bombs and bomb.due(now):
                out.append(self.factory.bomb(self.rng.uniform(lo, hi), target))
                bomb.reschedule(now, speedup)
        self._update_limiter(now, mode, out, speedup)
        self._update_grenades(now, mode, alive, out, speedup)
        return out

    def _update_limiter(self, now: float, mode: "BaseGameMode", out: list[BaseEntity], speedup: float) -> None:
        """Spawn the single allowed barrier limiter.

        :param now: match time in seconds.
        :type now: float
        :param mode: running mode.
        :type mode: fruit_knight.modes.base.BaseGameMode
        :param out: list receiving new entities.
        :type out: list[fruit_knight.entities.base.BaseEntity]
        :param speedup: hazard speed-up factor.
        :type speedup: float
        """
        if not (self.setup.enable_limiters and self._limiter_allowed and self._limiter.due(now)):
            return
        if mode.count_alive(BarrierLimiter) > 0:
            self._limiter.next_time = now + RETRY_DELAY
            return
        out.append(self.factory.limiter())
        self._limiter.reschedule(now, speedup)

    def _update_grenades(self, now: float, mode: "BaseGameMode", alive: list[int], out: list[BaseEntity], speedup: float) -> None:
        """Spawn holders and throwers, doubling them per lane in versus modes.

        :param now: match time in seconds.
        :type now: float
        :param mode: running mode.
        :type mode: fruit_knight.modes.base.BaseGameMode
        :param alive: ids of non-eliminated players.
        :type alive: list[int]
        :param out: list receiving new entities.
        :type out: list[fruit_knight.entities.base.BaseEntity]
        :param speedup: hazard speed-up factor.
        :type speedup: float
        """
        versus = self.lanes != [None]
        targets = [lane for lane in self.lanes if lane is not None] if versus else [self._target(None, alive)]
        if not targets or targets[0] is None:
            return
        if self.setup.enable_holders and self._holder.due(now):
            if mode.count_alive(Holder) > 0:
                self._holder.next_time = now + RETRY_DELAY
            else:
                for pid in targets:
                    lo, hi = self.sector(pid)
                    out.append(self.factory.holder(self.rng.uniform(lo, hi), pid))
                self._holder.reschedule(now, speedup)
        if self.setup.enable_throwers and self._thrower.due(now):
            if mode.count_alive(Thrower) > 0:
                self._thrower.next_time = now + RETRY_DELAY
            else:
                for pid in targets:
                    lo, hi = self.sector(pid)
                    zone = (
                        self.factory.target_zone("top", pid, (lo, hi)) if versus else self.factory.target_zone()
                    )
                    out.append(zone)
                    out.append(self.factory.thrower(self.rng.uniform(lo, hi), pid, zone))
                self._thrower.reschedule(now, speedup)
