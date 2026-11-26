"""Shared enumerations and constant tables."""

from __future__ import annotations

from enum import Enum


class HandState(str, Enum):
    """Static hand postures recognised by the gesture classifier."""

    KNIFE_HAND = "knife_hand"
    OPEN_PALM = "open_palm"
    CLOSED_FIST = "closed_fist"
    UNKNOWN = "unknown"


class TrackingMode(str, Enum):
    """Available computer vision pipelines."""

    POSE_HANDS = "pose_hands"
    HANDS_ONLY = "hands_only"


class ModeId(str, Enum):
    """Identifiers of the game modes."""

    ENDURANCE_1P = "1p_endurance"
    ENDURANCE_NP = "np_endurance"
    COMPETITION_NP = "np_competition"
    FOOTBALL_2P = "2p_football"


class EntityKind(str, Enum):
    """Entity categories."""

    FRUIT = "fruit"
    BOMB = "bomb"
    LIMITER = "limiter"
    HOLDER = "holder"
    THROWER = "thrower"
    TARGET_ZONE = "target_zone"


class PenaltyReason(str, Enum):
    """Causes of a player penalty."""

    MISS = "miss"
    BOMB = "bomb"
    GRENADE = "grenade"
    GOAL = "goal"


# Pymunk collision categories (bit masks) used by shape filters.
CATEGORY_ENTITY = 0b001
CATEGORY_LIMITER = 0b010
CATEGORY_TARGET = 0b100

# Pymunk collision types used by collision handlers.
COLLISION_ENTITY = 1
COLLISION_LIMITER = 2
COLLISION_TARGET = 3

# MediaPipe hand landmark indices.
WRIST = 0
INDEX_MCP, INDEX_PIP, INDEX_TIP = 5, 6, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP = 9, 10, 12
RING_MCP, RING_PIP, RING_TIP = 13, 14, 16
PINKY_MCP, PINKY_PIP, PINKY_TIP = 17, 18, 20

# (PIP, TIP) joint pairs of the four long fingers.
FINGER_JOINTS = (
    (INDEX_PIP, INDEX_TIP),
    (MIDDLE_PIP, MIDDLE_TIP),
    (RING_PIP, RING_TIP),
    (PINKY_PIP, PINKY_TIP),
)
# Adjacent fingertip pairs used to measure finger adduction.
ADJACENT_TIPS = ((INDEX_TIP, MIDDLE_TIP), (MIDDLE_TIP, RING_TIP), (RING_TIP, PINKY_TIP))
# Landmarks averaged to obtain the palm centre.
PALM_LANDMARKS = (WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP)

HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
)

# MediaPipe pose landmark indices.
NOSE = 0
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_WRIST, RIGHT_WRIST = 15, 16
LEFT_HIP, RIGHT_HIP = 23, 24

POSE_CONNECTIONS = (
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24), (23, 25), (25, 27),
    (24, 26), (26, 28), (15, 17), (15, 19), (16, 18), (16, 20),
)
