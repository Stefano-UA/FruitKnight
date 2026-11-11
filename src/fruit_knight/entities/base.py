"""Base classes of all game entities."""

from __future__ import annotations

import itertools
import random

import pymunk

from fruit_knight.physics.kinematics import effective_gravity
from fruit_knight.physics.world import ENTITY_FILTER, PhysicsWorld
from fruit_knight.utils.constants import COLLISION_ENTITY, EntityKind
from fruit_knight.utils.math_utils import limit_vector

Vec = tuple[float, float]
_ids = itertools.count(1)


class BaseEntity:
    """Minimal entity owning a Pymunk body and shape."""

    kind: EntityKind

    def __init__(self, world: PhysicsWorld) -> None:
        """Initialise bookkeeping.

        :param world: physics world the entity lives in.
        :type world: fruit_knight.physics.world.PhysicsWorld
        """
        self.id = next(_ids)
        self.world = world
        self.alive = True
        self.age = 0.0
        self.body: pymunk.Body | None = None
        self.shape: pymunk.Shape | None = None

    @property
    def position(self) -> Vec:
        """Report body position.

        :return: position in screen pixels.
        :rtype: tuple[float, float]
        """
        assert self.body is not None
        return self.body.position.x, self.body.position.y

    def update(self, dt: float) -> None:
        """Advance entity-specific logic.

        :param dt: time step in seconds.
        :type dt: float
        """
        self.age += dt

    def remove(self) -> None:
        """Detach entity from the physics world and mark it dead."""
        if self.body is not None and self.shape is not None:
            self.world.remove(self.body, self.shape)
        self.alive = False


class Projectile(BaseEntity):
    """Round, weighted entity launched into the screen (fruit, bomb, holder, thrower)."""

    graspable = True

    def __init__(
        self,
        world: PhysicsWorld,
        position: Vec,
        velocity: Vec,
        weight: float,
        radius: float,
        elasticity: float,
        friction: float,
        target_player: int | None,
        rng: random.Random,
    ) -> None:
        """Create projectile with per-entity effective gravity.

        :param world: physics world.
        :type world: fruit_knight.physics.world.PhysicsWorld
        :param position: spawn position in pixels.
        :type position: tuple[float, float]
        :param velocity: initial velocity in pixels per second.
        :type velocity: tuple[float, float]
        :param weight: weight factor applied to gravity.
        :type weight: float
        :param radius: collision radius in pixels.
        :type radius: float
        :param elasticity: bounce coefficient.
        :type elasticity: float
        :param friction: friction coefficient.
        :type friction: float
        :param target_player: player assigned to this entity, if any.
        :type target_player: int | None
        :param rng: random generator for spin.
        :type rng: random.Random
        """
        super().__init__(world)
        self.weight = weight
        self.radius = radius
        self.g_eff = effective_gravity(world.cfg.gravity, weight)
        self.target_player = target_player
        self.held_by: str | None = None  # key of the hand holding this entity
        self.last_holder: int | None = None  # player who grabbed it last
        self.last_thrower: int | None = None  # player who released it last
        self.zone_contacts: set = set()
        self._max_speed = world.cfg.max_entity_speed

        body = pymunk.Body(weight, pymunk.moment_for_circle(weight, 0.0, radius))
        body.position = position
        body.velocity = velocity
        body.angular_velocity = rng.uniform(-world.cfg.max_spin, world.cfg.max_spin)
        body.velocity_func = self._integrate
        shape = pymunk.Circle(body, radius)
        shape.elasticity = elasticity
        shape.friction = friction
        shape.filter = ENTITY_FILTER
        shape.collision_type = COLLISION_ENTITY
        self.body, self.shape = body, shape
        world.add(body, shape, self)

    def _integrate(self, body: pymunk.Body, gravity: Vec, damping: float, dt: float) -> None:
        """Integrate velocity with this entity's own gravity ``g_eff = g0 * w``.

        :param body: integrated body.
        :type body: pymunk.Body
        :param gravity: space gravity (unused, replaced by per-entity gravity).
        :type gravity: tuple[float, float]
        :param damping: space damping factor.
        :type damping: float
        :param dt: sub-step in seconds.
        :type dt: float
        """
        if self.held_by is not None:
            body.velocity = (0.0, 0.0)
            return
        pymunk.Body.update_velocity(body, (0.0, self.g_eff), damping, dt)

    @property
    def velocity(self) -> Vec:
        """Report body velocity.

        :return: velocity in pixels per second.
        :rtype: tuple[float, float]
        """
        assert self.body is not None
        return self.body.velocity.x, self.body.velocity.y

    def grab(self, hand_key: str, player_id: int) -> None:
        """Lock entity to a hand; it stops colliding while held.

        :param hand_key: identifier of the grabbing hand.
        :type hand_key: str
        :param player_id: player owning the hand.
        :type player_id: int
        """
        assert self.shape is not None
        self.held_by = hand_key
        self.last_holder = player_id
        self.shape.sensor = True

    def move_to(self, point: Vec) -> None:
        """Teleport held entity to a point (hand palm centre).

        :param point: target position in pixels.
        :type point: tuple[float, float]
        """
        assert self.body is not None
        self.body.position = point
        self.body.velocity = (0.0, 0.0)
        self.world.space.reindex_shapes_for_body(self.body)

    def release(self, velocity: Vec, player_id: int | None) -> None:
        """Detach from the hand and launch with inertia.

        :param velocity: velocity in pixels per second applied immediately.
        :type velocity: tuple[float, float]
        :param player_id: player who released it.
        :type player_id: int | None
        """
        assert self.body is not None and self.shape is not None
        self.held_by = None
        self.shape.sensor = False
        self.last_thrower = player_id
        self.body.velocity = limit_vector(velocity, self._max_speed)

    def exit_side(self) -> str | None:
        """Detect whether the entity left the playfield.

        :return: ``"bottom"``, ``"left"``, ``"right"`` or ``None``.
        :rtype: str | None
        """
        x, y = self.position
        margin = self.world.cfg.exit_margin
        if y > self.world.height + margin and self.velocity[1] > 0:
            return "bottom"
        if x < -margin:
            return "left"
        if x > self.world.width + margin:
            return "right"
        return None
