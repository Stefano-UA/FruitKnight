"""Static hand posture classification from 21 MediaPipe landmarks."""

from __future__ import annotations

import numpy as np

from fruit_knight.config.schema import GestureConfig
from fruit_knight.utils.constants import (
    ADJACENT_TIPS,
    FINGER_JOINTS,
    MIDDLE_MCP,
    WRIST,
    HandState,
)


def palm_size(points: np.ndarray) -> float:
    """Measure palm size as wrist-to-middle-MCP distance.

    :param points: landmark array of shape ``(21, 2)`` in aspect-correct units.
    :type points: numpy.ndarray
    :return: palm size, never below a small epsilon.
    :rtype: float
    """
    return max(float(np.linalg.norm(points[MIDDLE_MCP] - points[WRIST])), 1e-6)


class GestureClassifier:
    """Rule-based classifier producing KNIFE_HAND, OPEN_PALM, CLOSED_FIST or UNKNOWN."""

    def __init__(self, cfg: GestureConfig) -> None:
        """Store thresholds.

        :param cfg: gesture thresholds.
        :type cfg: fruit_knight.config.schema.GestureConfig
        """
        self._cfg = cfg

    def finger_flags(self, points: np.ndarray) -> tuple[int, int]:
        """Count extended and curled long fingers.

        :param points: landmark array of shape ``(21, 2)`` in aspect-correct units.
        :type points: numpy.ndarray
        :return: number of extended fingers and number of curled fingers.
        :rtype: tuple[int, int]
        """
        wrist = points[WRIST]
        extended = curled = 0
        for pip, tip in FINGER_JOINTS:
            tip_dist = float(np.linalg.norm(points[tip] - wrist))
            pip_dist = float(np.linalg.norm(points[pip] - wrist))
            if tip_dist > self._cfg.extended_ratio * pip_dist:
                extended += 1
            elif tip_dist < self._cfg.fist_curl_ratio * pip_dist:
                curled += 1
        return extended, curled

    def spread_ratio(self, points: np.ndarray) -> float:
        """Measure largest gap between adjacent fingertips relative to palm size.

        :param points: landmark array of shape ``(21, 2)`` in aspect-correct units.
        :type points: numpy.ndarray
        :return: dimensionless spread ratio.
        :rtype: float
        """
        gaps = [float(np.linalg.norm(points[a] - points[b])) for a, b in ADJACENT_TIPS]
        return max(gaps) / palm_size(points)

    def classify(self, points: np.ndarray) -> HandState:
        """Classify one hand posture.

        :param points: landmark array of shape ``(21, 2)`` in aspect-correct units.
        :type points: numpy.ndarray
        :return: detected posture, ``UNKNOWN`` when ambiguous.
        :rtype: fruit_knight.utils.constants.HandState
        """
        extended, curled = self.finger_flags(points)
        if extended == len(FINGER_JOINTS):
            adducted = self.spread_ratio(points) < self._cfg.knife_finger_spread_max_ratio
            return HandState.KNIFE_HAND if adducted else HandState.OPEN_PALM
        if curled >= self._cfg.min_curled_fingers:
            return HandState.CLOSED_FIST
        return HandState.UNKNOWN


class StateDebouncer:
    """Suppress single-frame posture flicker."""

    def __init__(self, frames: int) -> None:
        """Create debouncer.

        :param frames: consecutive identical readings required to switch posture.
        :type frames: int
        """
        self._frames = max(1, frames)
        self.state = HandState.UNKNOWN
        self._candidate = HandState.UNKNOWN
        self._count = 0

    def update(self, raw: HandState) -> HandState:
        """Feed a raw reading.

        :param raw: classifier output for the current frame.
        :type raw: fruit_knight.utils.constants.HandState
        :return: stable posture; ``UNKNOWN`` readings never replace a known posture.
        :rtype: fruit_knight.utils.constants.HandState
        """
        if raw == HandState.UNKNOWN or raw == self.state:
            self._candidate, self._count = self.state, 0
            return self.state
        if raw == self._candidate:
            self._count += 1
        else:
            self._candidate, self._count = raw, 1
        if self._count >= self._frames:
            self.state, self._count = raw, 0
        return self.state
