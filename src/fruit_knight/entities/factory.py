"""Factory creating configured, randomly launched entities."""

from __future__ import annotations

import random

from fruit_knight.config.schema import GameConfig
from fruit_knight.entities.base import BaseEntity
from fruit_knight.entities.bomb import Bomb
from fruit_knight.entities.fruit import Fruit
from fruit_knight.entities.holder import Holder
from fruit_knight.entities.limiter import BarrierLimiter
from fruit_knight.entities.target_zone import TargetZone
from fruit_knight.entities.thrower import Thrower
from fruit_knight.physics.kinematics import sample_launch
from fruit_knight.physics.world import PhysicsWorld
from fruit_knight.utils.math_utils import rand_range


class EntityFactory:
    """Builds entities with random positions and launch velocities from the configuration."""

    def __init__(self, cfg: GameConfig, world: PhysicsWorld, rng: random.Random) -> None:
        """Create factory.

        :param cfg: full game configuration.
        :type cfg: fruit_knight.config.schema.GameConfig
        :param world: physics world receiving the entities.
        :type world: fruit_knight.physics.world.PhysicsWorld
        :param rng: random generator.
        :type rng: random.Random
        """
        self.cfg = cfg
        self.world = world
        self.rng = rng

    def _launch(self, profile, weight: float, radius: float, x: float) -> tuple[tuple[float, float], tuple[float, float]]:
        """Compute spawn position and velocity.

        :param profile: random launch ranges.
        :type profile: fruit_knight.config.schema.LaunchProfile
        :param weight: entity weight factor.
        :type weight: float
        :param radius: entity radius in pixels.
        :type radius: float
        :param x: horizontal spawn coordinate in pixels.
        :type x: float
        :return: spawn position and launch velocity.
        :rtype: tuple[tuple[float, float], tuple[float, float]]
        """
        w, h = self.world.width, self.world.height
        position = (x, h + radius + self.cfg.physics.spawn_offset)
        velocity = sample_launch(self.rng, profile, self.cfg.physics.gravity, weight, h, x, w, w * self.cfg.spawning.spawn_margin_ratio)
        return position, velocity

    def pick_fruit_subtype(self) -> str:
        """Choose a fruit subtype using ``spawn_weight`` probabilities.

        :return: subtype key.
        :rtype: str
        """
        names = list(self.cfg.fruits.subtypes)
        weights = [self.cfg.fruits.subtypes[n].spawn_weight for n in names]
        return self.rng.choices(names, weights)[0]

    def fruit(self, x: float, target_player: int | None, subtype: str | None = None) -> Fruit:
        """Spawn a fruit.

        :param x: horizontal spawn coordinate in pixels.
        :type x: float
        :param target_player: player penalised on a miss.
        :type target_player: int | None
        :param subtype: fruit subtype; random when omitted.
        :type subtype: str | None
        :return: new fruit.
        :rtype: fruit_knight.entities.fruit.Fruit
        """
        name = subtype or self.pick_fruit_subtype()
        spec = self.cfg.fruits.subtypes[name]
        pos, vel = self._launch(self.cfg.fruits.launch, spec.weight, spec.radius, x)
        return Fruit(self.world, self.cfg.fruits, name, pos, vel, target_player, self.rng)

    def bomb(self, x: float, target_player: int | None) -> Bomb:
        """Spawn a bomb.

        :param x: horizontal spawn coordinate in pixels.
        :type x: float
        :param target_player: player assigned to the bomb.
        :type target_player: int | None
        :return: new bomb.
        :rtype: fruit_knight.entities.bomb.Bomb
        """
        c = self.cfg.bomb
        pos, vel = self._launch(c.launch, c.weight, c.radius, x)
        return Bomb(self.world, c, pos, vel, target_player, self.rng)

    def holder(self, x: float, target_player: int | None) -> Holder:
        """Spawn a holder grenade.

        :param x: horizontal spawn coordinate in pixels.
        :type x: float
        :param target_player: player responsible for it.
        :type target_player: int | None
        :return: new holder.
        :rtype: fruit_knight.entities.holder.Holder
        """
        c = self.cfg.holder
        pos, vel = self._launch(c.launch, c.weight, c.radius, x)
        return Holder(self.world, c, pos, vel, target_player, self.rng)

    def target_zone(self, side: str | None = None, player_id: int | None = None, x_bounds: tuple[float, float] | None = None) -> TargetZone:
        """Spawn a target zone on a random or given margin.

        :param side: ``"left"``, ``"right"`` or ``"top"``; random when omitted.
        :type side: str | None
        :param player_id: owner player for versus modes.
        :type player_id: int | None
        :param x_bounds: horizontal range allowed for top-margin zones.
        :type x_bounds: tuple[float, float] | None
        :return: new zone.
        :rtype: fruit_knight.entities.target_zone.TargetZone
        """
        c = self.cfg.thrower
        w, h = self.world.width, self.world.height
        side = side or self.rng.choice(("left", "right", "top"))
        if side == "top":
            lo, hi = x_bounds or (0.0, float(w))
            length = min(c.zone_length_ratio * w, hi - lo)
            x = self.rng.uniform(lo, hi - length)
            rect = (x, 0.0, length, c.zone_thickness)
        else:
            length = c.zone_length_ratio * h
            y = self.rng.uniform(0.0, h * 0.7 - length)
            x = 0.0 if side == "left" else w - c.zone_thickness
            rect = (x, max(0.0, y), c.zone_thickness, length)
        return TargetZone(self.world, rect, side, player_id)

    def thrower(self, x: float, target_player: int | None, zone: TargetZone) -> Thrower:
        """Spawn a thrower grenade bound to a zone.

        :param x: horizontal spawn coordinate in pixels.
        :type x: float
        :param target_player: player responsible for it.
        :type target_player: int | None
        :param zone: zone to deliver it to.
        :type zone: fruit_knight.entities.target_zone.TargetZone
        :return: new thrower.
        :rtype: fruit_knight.entities.thrower.Thrower
        """
        c = self.cfg.thrower
        pos, vel = self._launch(c.launch, c.weight, c.radius, x)
        return Thrower(self.world, c, pos, vel, target_player, zone, self.rng)

    def limiter(self) -> BarrierLimiter:
        """Spawn a barrier limiter at a random edge, height and inclination.

        :return: new limiter.
        :rtype: fruit_knight.entities.limiter.BarrierLimiter
        """
        c = self.cfg.limiter
        h = self.world.height
        side = self.rng.choice(("left", "right"))
        y = rand_range(self.rng, (c.min_y_ratio * h, c.max_y_ratio * h))
        incline = self.rng.uniform(-c.max_incline_deg, c.max_incline_deg)
        return BarrierLimiter(self.world, c, side, y, incline, rand_range(self.rng, c.lifetime_range))


def remove_all(entities: list[BaseEntity]) -> None:
    """Remove every entity from the physics world.

    :param entities: entities to dispose.
    :type entities: list[fruit_knight.entities.base.BaseEntity]
    """
    for entity in entities:
        entity.remove()
    entities.clear()
