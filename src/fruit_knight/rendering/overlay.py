"""Skeleton (mannequin) and hand landmark overlay drawn over the camera feed."""

from __future__ import annotations

import pygame

from fruit_knight.rendering.draw_utils import alpha_circle
from fruit_knight.rendering.fonts import FontCache
from fruit_knight.utils.constants import HAND_CONNECTIONS, NOSE, POSE_CONNECTIONS, HandState
from fruit_knight.vision.hands import HandSample
from fruit_knight.vision.trackers import PoseObservation

Color = tuple[int, int, int]
STATE_LABELS = {
    HandState.KNIFE_HAND: "KNIFE",
    HandState.OPEN_PALM: "PALM",
    HandState.CLOSED_FIST: "FIST",
    HandState.UNKNOWN: "",
}


def draw_poses(surface: pygame.Surface, poses: list[PoseObservation], colors: list[Color], fonts: FontCache) -> None:
    """Draw each player's mannequin in their colour.

    :param surface: target surface (viewport sized).
    :type surface: pygame.Surface
    :param poses: pose observations with player ids.
    :type poses: list[fruit_knight.vision.trackers.PoseObservation]
    :param colors: player colours indexed by ``player_id - 1``.
    :type colors: list[tuple[int, int, int]]
    :param fonts: font cache for the player tags.
    :type fonts: fruit_knight.rendering.fonts.FontCache
    """
    w, h = surface.get_size()
    for pose in poses:
        color = colors[(pose.player_id - 1) % len(colors)]
        pts = [(float(x) * w, float(y) * h) for x, y in pose.landmarks]
        for a, b in POSE_CONNECTIONS:
            pygame.draw.line(surface, (0, 0, 0), pts[a], pts[b], 9)
            pygame.draw.line(surface, color, pts[a], pts[b], 5)
        for i in (11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28):
            pygame.draw.circle(surface, color, pts[i], 7)
            pygame.draw.circle(surface, (255, 255, 255), pts[i], 7, 2)
        head = pts[NOSE]
        pygame.draw.circle(surface, color, head, 22, 4)
        fonts.draw_centered(surface, f"P{pose.player_id}", 22, color, (head[0], head[1] - 40))


def draw_hands(surface: pygame.Surface, samples: dict[str, HandSample], colors: list[Color], fonts: FontCache, show_labels: bool = True) -> None:
    """Draw tracked hands with posture feedback.

    :param surface: target surface (viewport sized).
    :type surface: pygame.Surface
    :param samples: current hand samples.
    :type samples: dict[str, fruit_knight.vision.hands.HandSample]
    :param colors: player colours indexed by ``player_id - 1``.
    :type colors: list[tuple[int, int, int]]
    :param fonts: font cache for state labels.
    :type fonts: fruit_knight.rendering.fonts.FontCache
    :param show_labels: print the posture name next to the hand.
    :type show_labels: bool
    """
    for s in samples.values():
        color = colors[(s.player_id - 1) % len(colors)]
        if s.landmarks is not None:
            pts = [(float(x), float(y)) for x, y in s.landmarks]
            for a, b in HAND_CONNECTIONS:
                pygame.draw.line(surface, color, pts[a], pts[b], 2)
            for p in pts:
                pygame.draw.circle(surface, color, p, 3)
        if s.state == HandState.KNIFE_HAND:
            pygame.draw.line(surface, (255, 255, 255), s.palm, s.tip, 8)
            pygame.draw.line(surface, color, s.palm, s.tip, 4)
            pygame.draw.circle(surface, color, s.palm, 12)
        elif s.state == HandState.OPEN_PALM:
            pygame.draw.circle(surface, color, s.palm, 30, 4)
        elif s.state == HandState.CLOSED_FIST:
            alpha_circle(surface, color, 200, s.palm, 24)
            pygame.draw.circle(surface, (255, 255, 255), s.palm, 24, 3)
        else:
            pygame.draw.circle(surface, color, s.palm, 14, 2)
        label = STATE_LABELS[s.state]
        if show_labels and label:
            fonts.draw_centered(surface, label, 16, color, (s.palm[0], s.palm[1] + 46), shadow=True)
