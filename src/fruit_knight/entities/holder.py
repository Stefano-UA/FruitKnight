"""Holder grenade (v1): grab and hold in a fist to defuse."""

from __future__ import annotations

import random
from enum import Enum

from fruit_knight.config.schema import HolderConfig
from fruit_knight.entities.base import Projectile
from fruit_knight.physics.world import PhysicsWorld
from fruit_knight.utils.constants import EntityKind
from fruit_knight.utils.math_utils import rand_range

Vec = tuple[float, float]


class HolderState(str, Enum):
    """Defusal state of a holder."""

    ACTIVE = "active"
    DEFUSED = "defused"


class Holder(Projectile):
    """Grenade whose countdown only advances while held in a closed fist."""

    kind = EntityKind.HOLDER

    def __init__(
        self,
        world: PhysicsWorld,
        cfg: HolderConfig,
        position: Vec,
        velocity: Vec,
        target_player: int | None,
        rng: random.Random,
    ) -> None:
        """Create holder with a random required hold duration.

        :param world: physics world.
        :type world: fruit_knight.physics.world.PhysicsWorld
        :param cfg: holder configuration.
        :type cfg: fruit_knight.config.schema.HolderConfig
        :param position: spawn position in pixels.
        :type position: tuple[float, float]
        :param velocity: initial velocity in pixels per second.
        :type velocity: tuple[float, float]
        :param target_player: player responsible for this grenade.
        :type target_player: int | None
        :param rng: random generator.
        :type rng: random.Random
        """
        super().__init__(world, position, velocity, cfg.weight, cfg.radius, cfg.elasticity, cfg.friction, target_player, rng)
        self.required = rand_range(rng, cfg.hold_duration_range)
        self.hold_time = 0.0
        self.state = HolderState.ACTIVE
        self.just_defused = False

    @property
    def progress(self) -> float:
        """Report defusal progress.

        :return: accumulated hold time ratio in ``[0, 1]``.
        :rtype: float
        """
        return min(1.0, self.hold_time / self.required)

    @property
    def remaining(self) -> float:
        """Report hold time still needed.

        :return: seconds left to defuse.
        :rtype: float
        """
        return max(0.0, self.required - self.hold_time)

    def update(self, dt: float) -> None:
        """Accumulate hold time while grabbed and defuse when complete.

        :param dt: time step in seconds.
        :type dt: float
        """
        super().update(dt)
        self.just_defused = False
        if self.state == HolderState.ACTIVE and self.held_by is not None:
            self.hold_time += dt
            if self.hold_time >= self.required:
                self.state = HolderState.DEFUSED
                self.just_defused = True
