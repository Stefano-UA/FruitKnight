"""Bomb hazard."""

from __future__ import annotations

import random

from fruit_knight.config.schema import BombConfig
from fruit_knight.entities.base import Projectile
from fruit_knight.physics.world import PhysicsWorld
from fruit_knight.utils.constants import EntityKind

Vec = tuple[float, float]


class Bomb(Projectile):
    """Bomb detonated only by a knife hand; palms and fists can safely move it."""

    kind = EntityKind.BOMB

    def __init__(
        self,
        world: PhysicsWorld,
        cfg: BombConfig,
        position: Vec,
        velocity: Vec,
        target_player: int | None,
        rng: random.Random,
    ) -> None:
        """Create bomb.

        :param world: physics world.
        :type world: fruit_knight.physics.world.PhysicsWorld
        :param cfg: bomb configuration.
        :type cfg: fruit_knight.config.schema.BombConfig
        :param position: spawn position in pixels.
        :type position: tuple[float, float]
        :param velocity: initial velocity in pixels per second.
        :type velocity: tuple[float, float]
        :param target_player: player assigned to this bomb.
        :type target_player: int | None
        :param rng: random generator.
        :type rng: random.Random
        """
        super().__init__(world, position, velocity, cfg.weight, cfg.radius, cfg.elasticity, cfg.friction, target_player, rng)
        self.exploded = False
