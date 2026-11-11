"""Tests for kinematics, weight-scaled gravity, limiter physics and target zones."""

from __future__ import annotations

import math
import random

from fruit_knight.config import load_config
from fruit_knight.entities import BarrierLimiter, EntityFactory, Holder, HolderState, Thrower
from fruit_knight.physics.kinematics import compute_launch_velocity, effective_gravity, flight_time
from fruit_knight.physics.world import PhysicsWorld

CFG = load_config()
SIZE = (CFG.window.width, CFG.window.height)


def make_world() -> tuple[PhysicsWorld, EntityFactory]:
    """Create world and factory with a fixed seed.

    :return: world and factory.
    :rtype: tuple[PhysicsWorld, EntityFactory]
    """
    world = PhysicsWorld(CFG.physics, SIZE)
    return world, EntityFactory(CFG, world, random.Random(7))


def run(world: PhysicsWorld, seconds: float, hook=None) -> None:
    """Step the world at 60 Hz.

    :param world: world to advance.
    :type world: PhysicsWorld
    :param seconds: simulated duration.
    :type seconds: float
    :param hook: callable invoked each frame with ``dt``.
    :type hook: typing.Callable | None
    """
    for _ in range(int(seconds * 60)):
        world.step(1 / 60)
        if hook:
            hook(1 / 60)


def test_launch_velocity_reaches_exact_apex() -> None:
    """Apex height equals the requested height for any weight."""
    for weight in (0.7, 1.0, 1.45):
        g = effective_gravity(620.0, weight)
        vx, vy = compute_launch_velocity(400.0, g, math.radians(10))
        assert math.isclose(vy * vy / (2 * g), 400.0, rel_tol=1e-9)
        assert math.isclose(vx, vy * math.tan(math.radians(10)))
        assert flight_time(vy, g) > 0


def test_heavier_objects_move_faster() -> None:
    """Heavier objects have higher launch speed and higher fall acceleration."""
    g_light, g_heavy = effective_gravity(620.0, 0.7), effective_gravity(620.0, 1.45)
    assert compute_launch_velocity(400, g_heavy, 0)[1] > compute_launch_velocity(400, g_light, 0)[1]
    assert g_heavy > g_light


def test_projectile_follows_ballistic_apex() -> None:
    """Simulated fruit reaches the configured apex height above its spawn point."""
    world, factory = make_world()
    fruit = factory.fruit(SIZE[0] / 2, 1, "apple")
    spawn_y = fruit.position[1]
    expected = -fruit.velocity[1] ** 2 / (2 * fruit.g_eff)
    top = spawn_y
    for _ in range(240):
        world.step(1 / 60)
        top = min(top, fruit.position[1])
    assert math.isclose(top - spawn_y, expected, rel_tol=0.03)


def test_fruit_falls_back_and_exits_bottom() -> None:
    """Unsliced fruit eventually exits through the bottom edge."""
    world, factory = make_world()
    fruit = factory.fruit(SIZE[0] / 2, 1, "watermelon")
    side = None
    for _ in range(60 * 8):
        world.step(1 / 60)
        side = fruit.exit_side()
        if side:
            break
    assert side in {"bottom", "left", "right"}


def test_grabbed_entity_ignores_gravity_and_release_applies_velocity() -> None:
    """Held entity stays locked; release launches it with the given velocity."""
    world, factory = make_world()
    holder = factory.holder(500, 1)
    holder.grab("p1:Right", 1)
    for _ in range(30):
        holder.move_to((500.0, 300.0))
        world.step(1 / 60)
    assert abs(holder.position[1] - 300.0) < 1.0
    holder.release((400.0, -200.0), 1)
    world.step(1 / 60)
    assert holder.velocity[0] > 300 and holder.last_thrower == 1


def test_holder_only_counts_down_while_held() -> None:
    """Hold timer advances only while grabbed and defuses at the required time."""
    world, factory = make_world()
    holder: Holder = factory.holder(500, 1)
    holder.update(1.0)
    assert holder.hold_time == 0.0
    holder.grab("k", 1)
    holder.update(holder.required + 0.01)
    assert holder.state == HolderState.DEFUSED and holder.just_defused


def test_ball_rolls_on_top_of_limiter_and_bounces_underneath() -> None:
    """Entities land and roll on an inclined beam; rising ones bounce off its underside."""
    world, factory = make_world()
    limiter = BarrierLimiter(world, CFG.limiter, "left", 400.0, 10.0, 30.0)
    limiter.length = limiter.max_length
    limiter.update(0.0)
    fruit = factory.fruit(800, 1, "apple")
    fruit.body.position = (400.0, 200.0)
    fruit.body.velocity = (0.0, 0.0)
    run(world, 1.0)
    # Sloping down to the right (alpha > 0): the apple lands on top and rolls rightwards.
    assert fruit.position[1] < 460 and fruit.velocity[0] > 10

    low = factory.fruit(800, 1, "apple")
    low.body.position = (300.0, 600.0)
    low.body.velocity = (0.0, -900.0)
    start_vy = None
    for _ in range(60):
        world.step(1 / 60)
        if start_vy is None and low.position[1] < 470:
            start_vy = low.velocity[1]
    assert low.position[1] > 400  # never crossed the beam


def test_limiter_stops_and_retracts() -> None:
    """Stopped limiter keeps its length; after expiry it retracts and dies."""
    world, _ = make_world()
    limiter = BarrierLimiter(world, CFG.limiter, "right", 300.0, 0.0, 3.0)
    limiter.update(0.5)
    length = limiter.length
    limiter.stop_requested = True
    limiter.update(0.5)
    assert limiter.stopped and limiter.length == length
    for _ in range(400):
        limiter.update(0.05)
        if not limiter.alive:
            break
    assert not limiter.alive


def test_thrower_reaches_target_zone_via_collision_handler() -> None:
    """Zone contact is tracked by the Pymunk handler and ignored while held."""
    world, factory = make_world()
    zone = factory.target_zone("left")
    thrower: Thrower = factory.thrower(600, 1, zone)
    x, y, w, h = zone.rect
    thrower.body.position = (x + w / 2, y + h / 2)
    thrower.body.velocity = (0.0, 0.0)
    thrower.grab("k", 1)
    world.step(1 / 60)
    assert zone in thrower.zone_contacts and not thrower.delivered
    thrower.release((0.0, 0.0), 1)
    assert thrower.delivered
