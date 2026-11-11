"""Thrower grenade (v2): grab and throw into a target zone."""

from __future__ import annotations

import random

from fruit_knight.config.schema import ThrowerConfig
from fruit_knight.entities.base import Projectile
from fruit_knight.entities.target_zone import TargetZone
from fruit_knight.physics.world import PhysicsWorld
from fruit_knight.utils.constants import EntityKind
from fruit_knight.utils.math_utils import rand_range
from fruit_knight.utils.timers import Timer

Vec = tuple[float, float]


class Thrower(Projectile):
    """Grenade that must be thrown through its target zone before it expires."""

    kind = EntityKind.THROWER

    def __init__(
        self,
        world: PhysicsWorld,
        cfg: ThrowerConfig,
        position: Vec,
        velocity: Vec,
        target_player: int | None,
        zone: TargetZone,
        rng: random.Random,
    ) -> None:
        """Create thrower linked to its target zone.

        :param world: physics world.
        :type world: fruit_knight.physics.world.PhysicsWorld
        :param cfg: thrower configuration.
        :type cfg: fruit_knight.config.schema.ThrowerConfig
        :param position: spawn position in pixels.
        :type position: tuple[float, float]
        :param velocity: initial velocity in pixels per second.
        :type velocity: tuple[float, float]
        :param target_player: player responsible for this grenade.
        :type target_player: int | None
        :param zone: target zone that completes the mission.
        :type zone: fruit_knight.entities.target_zone.TargetZone
        :param rng: random generator.
        :type rng: random.Random
        """
        super().__init__(world, position, velocity, cfg.weight, cfg.radius, cfg.elasticity, cfg.friction, target_player, rng)
        self.zone = zone
        self.expiry = Timer(rand_range(rng, cfg.expiration_range))

    def update(self, dt: float) -> None:
        """Advance expiry timer.

        :param dt: time step in seconds.
        :type dt: float
        """
        super().update(dt)
        self.expiry.update(dt)

    @property
    def delivered(self) -> bool:
        """Report whether the thrower reached its target zone after release.

        :return: True when overlapping the zone and not held.
        :rtype: bool
        """
        return self.held_by is None and self.zone in self.zone_contacts
