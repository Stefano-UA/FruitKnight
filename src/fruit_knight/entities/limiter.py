"""Barrier limiter: advancing trunk / retractable beam."""

from __future__ import annotations

import math

import pymunk

from fruit_knight.config.schema import LimiterConfig
from fruit_knight.entities.base import BaseEntity
from fruit_knight.physics.world import LIMITER_FILTER, PhysicsWorld
from fruit_knight.utils.constants import COLLISION_LIMITER, EntityKind
from fruit_knight.utils.timers import Timer

Vec = tuple[float, float]
# Initial length so the segment is never degenerate.
MIN_LENGTH = 1.0


class BarrierLimiter(BaseEntity):
    """Kinematic beam entering from a vertical edge; an open palm on its tip halts it."""

    kind = EntityKind.LIMITER

    def __init__(self, world: PhysicsWorld, cfg: LimiterConfig, side: str, y: float, incline_deg: float, lifetime: float) -> None:
        """Create limiter at a screen edge.

        :param world: physics world.
        :type world: fruit_knight.physics.world.PhysicsWorld
        :param cfg: limiter configuration.
        :type cfg: fruit_knight.config.schema.LimiterConfig
        :param side: ``"left"`` or ``"right"`` spawn edge.
        :type side: str
        :param y: spawn height in pixels.
        :type y: float
        :param incline_deg: inclination from the horizontal in degrees.
        :type incline_deg: float
        :param lifetime: total lifetime ``T_limit`` in seconds.
        :type lifetime: float
        """
        super().__init__(world)
        self.cfg = cfg
        self.side = side
        self.incline_deg = incline_deg
        alpha = math.radians(incline_deg)
        sign = 1.0 if side == "left" else -1.0
        self.origin: Vec = (0.0 if side == "left" else float(world.width), y)
        self.direction: Vec = (sign * math.cos(alpha), math.sin(alpha))
        # Length at which the tip reaches the opposite vertical edge.
        self.max_length = world.width / math.cos(alpha)
        self.length = MIN_LENGTH
        self.lifetime = Timer(lifetime)
        self.retracting = False
        self.stop_requested = False
        self.stopped = False

        body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        body.position = self.origin
        shape = pymunk.Segment(body, (0.0, 0.0), self._local_tip(), cfg.thickness / 2)
        shape.elasticity = cfg.elasticity
        shape.friction = cfg.friction
        shape.filter = LIMITER_FILTER
        shape.collision_type = COLLISION_LIMITER
        self.body, self.shape = body, shape
        world.add(body, shape, self)

    def _local_tip(self) -> Vec:
        """Compute tip position relative to the body origin.

        :return: local tip coordinates in pixels.
        :rtype: tuple[float, float]
        """
        return self.direction[0] * self.length, self.direction[1] * self.length

    @property
    def tip(self) -> Vec:
        """Report leading tip position.

        :return: tip in screen pixels.
        :rtype: tuple[float, float]
        """
        lx, ly = self._local_tip()
        return self.origin[0] + lx, self.origin[1] + ly

    @property
    def angle(self) -> float:
        """Report beam direction angle.

        :return: angle of the direction vector in radians (screen space).
        :rtype: float
        """
        return math.atan2(self.direction[1], self.direction[0])

    def update(self, dt: float) -> None:
        """Extend, hold or retract the beam.

        :param dt: time step in seconds.
        :type dt: float
        """
        super().update(dt)
        self.lifetime.update(dt)
        self.stopped = self.stop_requested and not self.retracting
        self.stop_requested = False
        if self.lifetime.done:
            self.retracting = True
        if self.retracting:
            self.length -= self.cfg.retract_speed * dt
            if self.length <= MIN_LENGTH:
                self.alive = False
                return
        elif not self.stopped and self.length < self.max_length:
            self.length = min(self.max_length, self.length + self.cfg.advance_speed * dt)
        assert self.shape is not None
        self.shape.unsafe_set_endpoints((0.0, 0.0), self._local_tip())  # type: ignore[attr-defined]
        self.world.space.reindex_shape(self.shape)
