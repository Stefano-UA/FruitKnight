"""Hand velocity estimation from a short position history."""

from __future__ import annotations

from collections import deque

Vec = tuple[float, float]


class VelocityEstimator:
    """Estimate instantaneous velocity in pixels per second with exponential smoothing."""

    def __init__(self, window_s: float, smoothing: float) -> None:
        """Create estimator.

        :param window_s: history length in seconds.
        :type window_s: float
        :param smoothing: EMA factor in ``(0, 1]``; 1 disables smoothing.
        :type smoothing: float
        """
        self._window = window_s
        self._alpha = smoothing
        self._history: deque[tuple[float, Vec]] = deque()
        self.velocity: Vec = (0.0, 0.0)

    def push(self, t: float, position: Vec) -> Vec:
        """Record a sample and update velocity.

        :param t: sample timestamp in seconds.
        :type t: float
        :param position: sample position in pixels.
        :type position: tuple[float, float]
        :return: smoothed velocity in pixels per second.
        :rtype: tuple[float, float]
        """
        self._history.append((t, position))
        while len(self._history) > 2 and t - self._history[0][0] > self._window:
            self._history.popleft()
        t0, p0 = self._history[0]
        span = t - t0
        if span > 1e-4:
            raw = ((position[0] - p0[0]) / span, (position[1] - p0[1]) / span)
            a = self._alpha
            self.velocity = (a * raw[0] + (1 - a) * self.velocity[0], a * raw[1] + (1 - a) * self.velocity[1])
        return self.velocity

    def reset(self) -> None:
        """Forget history and zero velocity."""
        self._history.clear()
        self.velocity = (0.0, 0.0)
