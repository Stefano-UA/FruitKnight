"""Launch kinematics: weight-scaled gravity and apex-height targeting."""

from __future__ import annotations

import math
import random

from fruit_knight.config.schema import LaunchProfile
from fruit_knight.utils.math_utils import rand_range


def effective_gravity(base_gravity: float, weight: float) -> float:
    """Scale base gravity by entity weight (``g_eff = g0 * w``).

    :param base_gravity: base gravitational acceleration in pixels per second squared.
    :type base_gravity: float
    :param weight: entity weight factor.
    :type weight: float
    :return: effective downward acceleration.
    :rtype: float
    """
    return base_gravity * weight


def compute_launch_velocity(target_height: float, effective_gravity: float, angle_rad: float) -> tuple[float, float]:
    """Compute initial 2D velocity vector to reach target apex height.

    :param target_height: vertical distance in pixels from spawn point to apex.
    :type target_height: float
    :param effective_gravity: gravity acceleration scaled by entity weight.
    :type effective_gravity: float
    :param angle_rad: launch trajectory angle in radians from vertical axis.
    :type angle_rad: float
    :return: horizontal and vertical velocity components in pixels per second.
    :rtype: tuple[float, float]
    """
    # v_y0 = sqrt(2 * g_eff * H) makes the apex exactly H above the spawn point.
    vy0 = math.sqrt(2.0 * effective_gravity * target_height)
    vx0 = vy0 * math.tan(angle_rad)
    return vx0, vy0


def flight_time(vy0: float, effective_gravity: float) -> float:
    """Compute time to return to the spawn height.

    :param vy0: initial upward speed in pixels per second.
    :type vy0: float
    :param effective_gravity: gravity acceleration scaled by entity weight.
    :type effective_gravity: float
    :return: round-trip time in seconds.
    :rtype: float
    """
    return 2.0 * vy0 / effective_gravity


def sample_launch(
    rng: random.Random,
    profile: LaunchProfile,
    base_gravity: float,
    weight: float,
    screen_height: float,
    spawn_x: float,
    screen_width: float,
    margin: float,
) -> tuple[float, float]:
    """Sample a random launch whose trajectory stays horizontally on screen.

    Launches starting inside the edge zones of ``profile`` move towards the opposite side, so the
    player never faces an object that leaves through the border it appeared next to.

    :param rng: random generator.
    :type rng: random.Random
    :param profile: random height and angle ranges.
    :type profile: fruit_knight.config.schema.LaunchProfile
    :param base_gravity: base gravity ``g0``.
    :type base_gravity: float
    :param weight: entity weight factor.
    :type weight: float
    :param screen_height: screen height in pixels.
    :type screen_height: float
    :param spawn_x: horizontal spawn position in pixels.
    :type spawn_x: float
    :param screen_width: screen width in pixels.
    :type screen_width: float
    :param margin: horizontal safety margin in pixels.
    :type margin: float
    :return: velocity ``(vx, vy)`` in screen coordinates (negative ``vy`` is upwards).
    :rtype: tuple[float, float]
    """
    g_eff = effective_gravity(base_gravity, weight)
    height = rand_range(rng, (profile.min_height_ratio, profile.max_height_ratio)) * screen_height
    angle = math.radians(rand_range(rng, (profile.min_angle_deg, profile.max_angle_deg)))
    vx, vy = compute_launch_velocity(height, g_eff, angle)
    zone = profile.edge_zone_ratio * screen_width
    if spawn_x < zone:
        vx = abs(vx)  # spawned near the left edge: always head towards the opposite side
    elif spawn_x > screen_width - zone:
        vx = -abs(vx)
    else:
        vx *= rng.choice((-1.0, 1.0))
    # Never let the arc reach the side borders: cap the drift so it lands inside the margins.
    t = flight_time(vy, g_eff)
    landing_x = spawn_x + vx * t
    low, high = margin, screen_width - margin
    if landing_x < low:
        vx = (low - spawn_x) / t
    elif landing_x > high:
        vx = (high - spawn_x) / t
    return vx, -vy
