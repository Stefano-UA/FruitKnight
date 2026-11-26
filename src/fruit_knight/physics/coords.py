"""Coordinate conversions between camera, viewport and Pymunk spaces."""

from __future__ import annotations

Vec = tuple[float, float]


class ViewportTransform:
    """Map normalised camera-frame coordinates to game viewport pixels."""

    def __init__(self, viewport: tuple[int, int]) -> None:
        """Create transform.

        :param viewport: viewport width and height in pixels.
        :type viewport: tuple[int, int]
        """
        self.width, self.height = viewport

    def to_viewport(self, nx: float, ny: float) -> Vec:
        """Convert normalised coordinates to viewport pixels.

        :param nx: horizontal coordinate in ``[0, 1]`` of the cropped, mirrored frame.
        :type nx: float
        :param ny: vertical coordinate in ``[0, 1]`` of the cropped, mirrored frame.
        :type ny: float
        :return: pixel position inside the viewport.
        :rtype: tuple[float, float]
        """
        return nx * self.width, ny * self.height

    def to_normalised(self, x: float, y: float) -> Vec:
        """Convert viewport pixels to normalised coordinates.

        :param x: horizontal pixel coordinate.
        :type x: float
        :param y: vertical pixel coordinate.
        :type y: float
        :return: normalised position.
        :rtype: tuple[float, float]
        """
        return x / self.width, y / self.height


def screen_to_pymunk(point: Vec) -> Vec:
    """Convert screen pixels to Pymunk coordinates.

    Pymunk runs in screen space (``+y`` down), so the mapping is the identity.

    :param point: screen position.
    :type point: tuple[float, float]
    :return: Pymunk position.
    :rtype: tuple[float, float]
    """
    return point


def pymunk_to_screen(point: Vec) -> Vec:
    """Convert Pymunk coordinates to screen pixels.

    :param point: Pymunk position.
    :type point: tuple[float, float]
    :return: screen position.
    :rtype: tuple[float, float]
    """
    return point
