"""Conversion of camera frames into pygame surfaces."""

from __future__ import annotations

import cv2
import numpy as np
import pygame


def frame_to_surface(frame_rgb: np.ndarray, size: tuple[int, int]) -> pygame.Surface:
    """Scale an RGB frame to a size and wrap it in a surface.

    :param frame_rgb: ``uint8`` image of shape ``(H, W, 3)``.
    :type frame_rgb: numpy.ndarray
    :param size: target width and height in pixels.
    :type size: tuple[int, int]
    :return: scaled surface without alpha.
    :rtype: pygame.Surface
    """
    scaled = cv2.resize(frame_rgb, size, interpolation=cv2.INTER_LINEAR)
    return pygame.image.frombuffer(scaled.tobytes(), size, "RGB").convert()


def fit_rect(source: tuple[int, int], target: pygame.Rect) -> pygame.Rect:
    """Compute the largest rectangle with the source aspect ratio inside a target.

    :param source: source width and height.
    :type source: tuple[int, int]
    :param target: container rectangle.
    :type target: pygame.Rect
    :return: letterboxed rectangle centred inside ``target``.
    :rtype: pygame.Rect
    """
    scale = min(target.width / source[0], target.height / source[1])
    rect = pygame.Rect(0, 0, int(source[0] * scale), int(source[1] * scale))
    rect.center = target.center
    return rect
