"""Sliceable fruit."""

from __future__ import annotations

import random

from fruit_knight.config.schema import FruitConfig, FruitSubtype
from fruit_knight.entities.base import Projectile
from fruit_knight.physics.world import PhysicsWorld
from fruit_knight.utils.constants import EntityKind

Vec = tuple[float, float]


class Fruit(Projectile):
    """Fruit that scores points when sliced by a knife hand."""

    kind = EntityKind.FRUIT

    def __init__(
        self,
        world: PhysicsWorld,
        cfg: FruitConfig,
        subtype: str,
        position: Vec,
        velocity: Vec,
        target_player: int | None,
        rng: random.Random,
    ) -> None:
        """Create fruit of a configured subtype.

        :param world: physics world.
        :type world: fruit_knight.physics.world.PhysicsWorld
        :param cfg: fruit family configuration.
        :type cfg: fruit_knight.config.schema.FruitConfig
        :param subtype: key inside ``cfg.subtypes``.
        :type subtype: str
        :param position: spawn position in pixels.
        :type position: tuple[float, float]
        :param velocity: initial velocity in pixels per second.
        :type velocity: tuple[float, float]
        :param target_player: player penalised if the fruit is missed.
        :type target_player: int | None
        :param rng: random generator.
        :type rng: random.Random
        """
        spec: FruitSubtype = cfg.subtypes[subtype]
        super().__init__(world, position, velocity, spec.weight, spec.radius, cfg.elasticity, cfg.friction, target_player, rng)
        self.subtype = subtype
        self.spec = spec
        self.points = spec.points
        self.sliced = False
