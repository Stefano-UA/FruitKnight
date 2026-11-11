"""Normalised region-of-interest (play area) helper."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MIN_ROI_SIDE = 0.1


@dataclass(frozen=True)
class RoiRect:
    """Rectangle in normalised camera coordinates ``[0, 1]``."""

    x: float = 0.0
    y: float = 0.0
    w: float = 1.0
    h: float = 1.0

    @staticmethod
    def full() -> "RoiRect":
        """Create full-frame ROI.

        :return: rectangle covering the whole frame.
        :rtype: RoiRect
        """
        return RoiRect(0.0, 0.0, 1.0, 1.0)

    @staticmethod
    def from_corners(x0: float, y0: float, x1: float, y1: float) -> "RoiRect":
        """Build clamped ROI from two arbitrary normalised corners.

        :param x0: first corner x.
        :type x0: float
        :param y0: first corner y.
        :type y0: float
        :param x1: opposite corner x.
        :type x1: float
        :param y1: opposite corner y.
        :type y1: float
        :return: ordered rectangle inside the frame; full frame if too small.
        :rtype: RoiRect
        """
        lx, hx = sorted((min(1.0, max(0.0, x0)), min(1.0, max(0.0, x1))))
        ly, hy = sorted((min(1.0, max(0.0, y0)), min(1.0, max(0.0, y1))))
        if hx - lx < MIN_ROI_SIDE or hy - ly < MIN_ROI_SIDE:
            return RoiRect.full()
        return RoiRect(lx, ly, hx - lx, hy - ly)

    def crop(self, frame: np.ndarray) -> np.ndarray:
        """Crop an image array to this ROI.

        :param frame: image of shape ``(H, W, C)``.
        :type frame: numpy.ndarray
        :return: view of the cropped region.
        :rtype: numpy.ndarray
        """
        h, w = frame.shape[:2]
        x0, y0 = int(self.x * w), int(self.y * h)
        x1, y1 = max(x0 + 1, int((self.x + self.w) * w)), max(y0 + 1, int((self.y + self.h) * h))
        return frame[y0:y1, x0:x1]

    @property
    def is_full(self) -> bool:
        """Report whether the ROI covers the whole frame.

        :return: True for the full-frame rectangle.
        :rtype: bool
        """
        return self.x <= 0.0 and self.y <= 0.0 and self.w >= 1.0 and self.h >= 1.0
