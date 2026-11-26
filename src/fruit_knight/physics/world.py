"""Pymunk space wrapper with collision handlers and fixed sub-stepping."""

from __future__ import annotations

from typing import Any

import pymunk

from fruit_knight.config.schema import PhysicsConfig
from fruit_knight.utils.constants import (
    CATEGORY_ENTITY,
    CATEGORY_LIMITER,
    CATEGORY_TARGET,
    COLLISION_ENTITY,
    COLLISION_TARGET,
)

# Shape filters keeping entities from colliding with each other.
ENTITY_FILTER = pymunk.ShapeFilter(categories=CATEGORY_ENTITY, mask=CATEGORY_LIMITER | CATEGORY_TARGET)
LIMITER_FILTER = pymunk.ShapeFilter(categories=CATEGORY_LIMITER, mask=CATEGORY_ENTITY)
TARGET_FILTER = pymunk.ShapeFilter(categories=CATEGORY_TARGET, mask=CATEGORY_ENTITY)


class PhysicsWorld:
    """Owns the Pymunk space and maps shapes back to game objects."""

    def __init__(self, cfg: PhysicsConfig, size: tuple[int, int]) -> None:
        """Create empty world.

        Gravity is applied per body in a custom velocity function, so the space gravity is zero.

        :param cfg: physics configuration.
        :type cfg: fruit_knight.config.schema.PhysicsConfig
        :param size: screen width and height in pixels.
        :type size: tuple[int, int]
        """
        self.cfg = cfg
        self.width, self.height = size
        self.space = pymunk.Space()
        self.space.gravity = (0.0, 0.0)
        self.space.damping = cfg.damping
        self._owners: dict[pymunk.Shape, Any] = {}
        self.space.on_collision(COLLISION_ENTITY, COLLISION_TARGET, begin=self._zone_begin, separate=self._zone_separate)

    # ------------------------------------------------------------ bookkeeping
    def add(self, body: pymunk.Body, shape: pymunk.Shape, owner: Any) -> None:
        """Insert body and shape, remembering the owning game object.

        :param body: rigid body.
        :type body: pymunk.Body
        :param shape: collision shape attached to ``body``.
        :type shape: pymunk.Shape
        :param owner: game object owning the shape.
        :type owner: typing.Any
        """
        if body.space is None:
            self.space.add(body)
        self.space.add(shape)
        self._owners[shape] = owner

    def remove(self, body: pymunk.Body, shape: pymunk.Shape) -> None:
        """Remove body and shape if present.

        :param body: rigid body.
        :type body: pymunk.Body
        :param shape: collision shape attached to ``body``.
        :type shape: pymunk.Shape
        """
        self._owners.pop(shape, None)
        if shape in self.space.shapes:
            self.space.remove(shape)
        if body in self.space.bodies:
            self.space.remove(body)

    def owner_of(self, shape: pymunk.Shape) -> Any:
        """Look up the game object owning a shape.

        :param shape: collision shape.
        :type shape: pymunk.Shape
        :return: owner or ``None``.
        :rtype: typing.Any
        """
        return self._owners.get(shape)

    # --------------------------------------------------------------- handlers
    def _zone_begin(self, arbiter: pymunk.Arbiter, space: pymunk.Space, data: Any) -> None:
        """Flag an entity entering a target zone.

        :param arbiter: collision arbiter.
        :type arbiter: pymunk.Arbiter
        :param space: owning space.
        :type space: pymunk.Space
        :param data: unused handler data.
        :type data: typing.Any
        """
        entity, zone = (self.owner_of(s) for s in arbiter.shapes)
        if entity is not None and zone is not None and hasattr(entity, "zone_contacts"):
            entity.zone_contacts.add(zone)

    def _zone_separate(self, arbiter: pymunk.Arbiter, space: pymunk.Space, data: Any) -> None:
        """Clear the flag when an entity leaves a target zone.

        :param arbiter: collision arbiter.
        :type arbiter: pymunk.Arbiter
        :param space: owning space.
        :type space: pymunk.Space
        :param data: unused handler data.
        :type data: typing.Any
        """
        entity, zone = (self.owner_of(s) for s in arbiter.shapes)
        if entity is not None and zone is not None and hasattr(entity, "zone_contacts"):
            entity.zone_contacts.discard(zone)

    # ------------------------------------------------------------------ step
    def step(self, dt: float) -> None:
        """Advance simulation using fixed sub-steps.

        :param dt: frame time in seconds.
        :type dt: float
        """
        sub = dt / self.cfg.substeps
        for _ in range(self.cfg.substeps):
            self.space.step(sub)
