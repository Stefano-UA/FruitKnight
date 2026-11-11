"""Small timer utilities driven by explicit time steps."""

from __future__ import annotations

import random

from fruit_knight.utils.math_utils import rand_range


class Timer:
    """Countdown timer advanced manually."""

    def __init__(self, duration: float) -> None:
        """Create a stopped-at-zero countdown.

        :param duration: total duration in seconds.
        :type duration: float
        """
        self.duration = duration
        self.elapsed = 0.0

    def update(self, dt: float) -> None:
        """Advance timer.

        :param dt: time step in seconds.
        :type dt: float
        """
        self.elapsed = min(self.duration, self.elapsed + dt)

    def reset(self) -> None:
        """Restart timer from zero."""
        self.elapsed = 0.0

    @property
    def remaining(self) -> float:
        """Report seconds left.

        :return: remaining seconds, never negative.
        :rtype: float
        """
        return max(0.0, self.duration - self.elapsed)

    @property
    def done(self) -> bool:
        """Report completion.

        :return: True once the full duration elapsed.
        :rtype: bool
        """
        return self.elapsed >= self.duration

    @property
    def progress(self) -> float:
        """Report completion ratio.

        :return: value in ``[0, 1]``.
        :rtype: float
        """
        return 1.0 if self.duration <= 0 else self.elapsed / self.duration


class ScheduledEvent:
    """Event firing at random moments of a match clock."""

    def __init__(self, rng: random.Random, initial_delay: tuple[float, float], interval: tuple[float, float]) -> None:
        """Schedule first firing after a random dead-time.

        :param rng: random generator.
        :type rng: random.Random
        :param initial_delay: dead-time range before the first firing.
        :type initial_delay: tuple[float, float]
        :param interval: range of gaps between later firings.
        :type interval: tuple[float, float]
        """
        self._rng = rng
        self._interval = interval
        self.next_time = rand_range(rng, initial_delay)

    def due(self, now: float) -> bool:
        """Check whether the event should fire.

        :param now: current match time in seconds.
        :type now: float
        :return: True when scheduled time has passed.
        :rtype: bool
        """
        return now >= self.next_time

    def reschedule(self, now: float, speedup: float = 1.0) -> None:
        """Pick next firing time.

        :param now: current match time in seconds.
        :type now: float
        :param speedup: divisor applied to the sampled gap.
        :type speedup: float
        """
        self.next_time = now + rand_range(self._rng, self._interval) / max(speedup, 1e-6)
