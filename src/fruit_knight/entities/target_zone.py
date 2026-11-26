"""Target zone (portal) receiving thrown grenades."""

from __future__ import annotations

import pymunk

from fruit_knight.entities.base import BaseEntity
from fruit_knight.physics.world import TARGET_FILTER, PhysicsWorld
from fruit_knight.utils.constants import COLLISION_TARGET, EntityKind


class TargetZone(BaseEntity):
    """Static rectangular sensor at a screen margin."""

    kind = EntityKind.TARGET_ZONE

    def __init__(self, world: PhysicsWorld, rect: tuple[float, float, float, float], side: str, player_id: int | None) -> None:
        """Create zone.

        :param world: physics world.
        :type world: fruit_knight.physics.world.PhysicsWorld
        :param rect: left, top, width and height in pixels.
        :type rect: tuple[float, float, float, float]
        :param side: ``"left"``, ``"right"`` or ``"top"`` margin.
        :type side: str
        :param player_id: player the zone belongs to (football), if any.
        :type player_id: int | None
        """
        super().__init__(world)
        self.rect = rect
        self.side = side
        self.player_id = player_id
        x, y, w, h = rect
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (x + w / 2, y + h / 2)
        shape = pymunk.Poly.create_box(body, (w, h))
        shape.sensor = True
        shape.filter = TARGET_FILTER
        shape.collision_type = COLLISION_TARGET
        self.body, self.shape = body, shape
        world.add(body, shape, self)

    def contains(self, point: tuple[float, float]) -> bool:
        """Test whether a point lies inside the zone.

        :param point: position in pixels.
        :type point: tuple[float, float]
        :return: True when inside the rectangle.
        :rtype: bool
        """
        x, y, w, h = self.rect
        return x <= point[0] <= x + w and y <= point[1] <= y + h
