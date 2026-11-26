"""Math helpers for geometry and random sampling."""

from __future__ import annotations

import math
import random

Vec = tuple[float, float]


def clamp(value: float, low: float, high: float) -> float:
    """Restrict value to a closed interval.

    :param value: input value.
    :type value: float
    :param low: lower bound.
    :type low: float
    :param high: upper bound.
    :type high: float
    :return: value limited to ``[low, high]``.
    :rtype: float
    """
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    """Interpolate linearly between two numbers.

    :param a: value at ``t = 0``.
    :type a: float
    :param b: value at ``t = 1``.
    :type b: float
    :param t: interpolation factor.
    :type t: float
    :return: interpolated value.
    :rtype: float
    """
    return a + (b - a) * t


def distance(a: Vec, b: Vec) -> float:
    """Compute Euclidean distance between two points.

    :param a: first point.
    :type a: tuple[float, float]
    :param b: second point.
    :type b: tuple[float, float]
    :return: distance in input units.
    :rtype: float
    """
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point_segment_distance(p: Vec, a: Vec, b: Vec) -> float:
    """Compute shortest distance from a point to a line segment.

    :param p: query point.
    :type p: tuple[float, float]
    :param a: segment start.
    :type a: tuple[float, float]
    :param b: segment end.
    :type b: tuple[float, float]
    :return: minimal distance in input units.
    :rtype: float
    """
    abx, aby = b[0] - a[0], b[1] - a[1]
    length_sq = abx * abx + aby * aby
    if length_sq < 1e-9:
        return distance(p, a)
    # Project p onto the segment and clamp the parameter to stay on it.
    t = clamp(((p[0] - a[0]) * abx + (p[1] - a[1]) * aby) / length_sq, 0.0, 1.0)
    return distance(p, (a[0] + t * abx, a[1] + t * aby))


def rand_range(rng: random.Random, bounds: tuple[float, float]) -> float:
    """Sample uniformly inside a ``(min, max)`` pair.

    :param rng: random generator.
    :type rng: random.Random
    :param bounds: lower and upper bound.
    :type bounds: tuple[float, float]
    :return: sampled value.
    :rtype: float
    """
    return rng.uniform(bounds[0], bounds[1])


def norm(v: Vec) -> float:
    """Compute vector magnitude.

    :param v: input vector.
    :type v: tuple[float, float]
    :return: Euclidean norm.
    :rtype: float
    """
    return math.hypot(v[0], v[1])


def limit_vector(v: Vec, max_length: float) -> Vec:
    """Scale vector down when it exceeds a maximum magnitude.

    :param v: input vector.
    :type v: tuple[float, float]
    :param max_length: magnitude ceiling.
    :type max_length: float
    :return: vector with magnitude at most ``max_length``.
    :rtype: tuple[float, float]
    """
    length = norm(v)
    if length <= max_length or length < 1e-9:
        return v
    scale = max_length / length
    return (v[0] * scale, v[1] * scale)


def format_time(seconds: float) -> str:
    """Format seconds as ``MM:SS``.

    :param seconds: non-negative duration.
    :type seconds: float
    :return: formatted clock string.
    :rtype: str
    """
    whole = max(0, int(seconds))
    return f"{whole // 60:02d}:{whole % 60:02d}"
