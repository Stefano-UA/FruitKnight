"""MediaPipe Tasks trackers: Pose+Hands and lightweight Hands-only."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from fruit_knight.config.schema import TrackingConfig
from fruit_knight.utils.constants import (
    LEFT_SHOULDER,
    LEFT_WRIST,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
    WRIST,
)

# Maximum normalised movement of a pose centroid between frames to keep its identity.
IDENTITY_MATCH_DISTANCE = 0.4
MAX_HANDS_PER_PLAYER = 2


@dataclass
class HandObservation:
    """One detected hand assigned to a player."""

    player_id: int
    label: str
    landmarks: np.ndarray  # shape (21, 2), normalised to the processed frame


@dataclass
class PoseObservation:
    """One detected body pose assigned to a player."""

    player_id: int
    landmarks: np.ndarray  # shape (33, 2), normalised to the processed frame


@dataclass
class TrackingResult:
    """Output of one processed camera frame."""

    frame: np.ndarray | None = None  # RGB, mirrored and ROI-cropped
    hands: list[HandObservation] = field(default_factory=list)
    poses: list[PoseObservation] = field(default_factory=list)
    timestamp: float = 0.0


def assign_hands_to_zones(wrist_xs: list[float], players: int) -> list[int]:
    """Assign hands to equal-width horizontal zones.

    :param wrist_xs: normalised wrist x coordinates in ``[0, 1]``.
    :type wrist_xs: list[float]
    :param players: number of players (zones).
    :type players: int
    :return: player id (1-based) per hand.
    :rtype: list[int]
    """
    return [min(players, max(1, int(x * players) + 1)) for x in wrist_xs]


def assign_hands_to_poses(
    hand_wrists: list[tuple[float, float]],
    pose_wrists: dict[int, list[tuple[float, float]]],
    max_distance: float,
) -> list[int | None]:
    """Assign each hand to the player whose pose wrist is closest.

    :param hand_wrists: normalised wrist position of each hand.
    :type hand_wrists: list[tuple[float, float]]
    :param pose_wrists: pose wrist positions per player id.
    :type pose_wrists: dict[int, list[tuple[float, float]]]
    :param max_distance: largest accepted normalised distance.
    :type max_distance: float
    :return: player id per hand, ``None`` when no pose is close enough.
    :rtype: list[int | None]
    """
    candidates = []
    for hi, hw in enumerate(hand_wrists):
        for pid, wrists in pose_wrists.items():
            best = min(math.hypot(hw[0] - w[0], hw[1] - w[1]) for w in wrists)
            candidates.append((best, hi, pid))
    candidates.sort()
    result: list[int | None] = [None] * len(hand_wrists)
    counts: dict[int, int] = {}
    for dist, hi, pid in candidates:
        if dist > max_distance:
            break
        if result[hi] is None and counts.get(pid, 0) < MAX_HANDS_PER_PLAYER:
            result[hi] = pid
            counts[pid] = counts.get(pid, 0) + 1
    return result


class PlayerIdentityTracker:
    """Keep consistent player ids for detected poses across frames."""

    def __init__(self, players: int) -> None:
        """Create tracker.

        :param players: number of players expected.
        :type players: int
        """
        self._players = players
        self._last: dict[int, tuple[float, float]] = {}

    def assign(self, centroids: list[tuple[float, float]]) -> list[int | None]:
        """Match pose centroids to persistent player ids.

        :param centroids: normalised torso centroid per detected pose.
        :type centroids: list[tuple[float, float]]
        :return: player id per pose, ``None`` for surplus poses.
        :rtype: list[int | None]
        """
        result: list[int | None] = [None] * len(centroids)
        used: set[int] = set()
        pairs = sorted(
            (math.hypot(c[0] - lx, c[1] - ly), i, pid)
            for i, c in enumerate(centroids)
            for pid, (lx, ly) in self._last.items()
        )
        for dist, i, pid in pairs:
            if dist <= IDENTITY_MATCH_DISTANCE and result[i] is None and pid not in used:
                result[i] = pid
                used.add(pid)
        free = [p for p in range(1, self._players + 1) if p not in used]
        # New bodies take the lowest free id, left-most body first.
        for i in sorted((i for i, r in enumerate(result) if r is None), key=lambda k: centroids[k][0]):
            if free:
                result[i] = free.pop(0)
        for c, pid in zip(centroids, result):
            if pid is not None:
                self._last[pid] = c
        return result


def fix_hand_labels(hands: list[HandObservation]) -> None:
    """Make hand labels unique within each player.

    :param hands: observations whose labels may collide.
    :type hands: list[HandObservation]
    """
    by_player: dict[int, list[HandObservation]] = {}
    for hand in hands:
        by_player.setdefault(hand.player_id, []).append(hand)
    for group in by_player.values():
        if len(group) == 2 and group[0].label == group[1].label:
            left_first = sorted(group, key=lambda h: h.landmarks[WRIST][0])
            left_first[0].label, left_first[1].label = "Left", "Right"


class BaseTracker(ABC):
    """Interface of frame-by-frame trackers."""

    @abstractmethod
    def process(self, rgb: np.ndarray, timestamp_ms: int) -> tuple[list[HandObservation], list[PoseObservation]]:
        """Detect hands (and poses) in an RGB frame.

        :param rgb: contiguous ``uint8`` image of shape ``(H, W, 3)``.
        :type rgb: numpy.ndarray
        :param timestamp_ms: strictly increasing timestamp in milliseconds.
        :type timestamp_ms: int
        :return: hand and pose observations with player ids assigned.
        :rtype: tuple[list[HandObservation], list[PoseObservation]]
        """

    def close(self) -> None:
        """Release native resources."""


def _create_hand_landmarker(model: Path, cfg: TrackingConfig, max_hands: int):
    """Build MediaPipe HandLandmarker in VIDEO mode.

    :param model: path of ``hand_landmarker.task``.
    :type model: pathlib.Path
    :param cfg: tracking configuration.
    :type cfg: fruit_knight.config.schema.TrackingConfig
    :param max_hands: maximum number of simultaneous hands.
    :type max_hands: int
    :return: configured landmarker.
    :rtype: mediapipe.tasks.python.vision.HandLandmarker
    """
    from mediapipe.tasks.python import BaseOptions, vision

    # Model bytes avoid native path issues with non-ASCII Windows folders.
    options = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_buffer=model.read_bytes()),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=max_hands,
        min_hand_detection_confidence=cfg.min_detection_confidence,
        min_hand_presence_confidence=cfg.min_detection_confidence,
        min_tracking_confidence=cfg.min_tracking_confidence,
    )
    return vision.HandLandmarker.create_from_options(options)


def _mp_image(rgb: np.ndarray):
    """Wrap an RGB array into a MediaPipe image.

    :param rgb: contiguous ``uint8`` RGB array.
    :type rgb: numpy.ndarray
    :return: MediaPipe image.
    :rtype: mediapipe.Image
    """
    import mediapipe as mp

    return mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))


def _hand_arrays(result) -> list[tuple[str, np.ndarray]]:
    """Convert a HandLandmarker result into label and landmark arrays.

    :param result: MediaPipe hand landmarker result.
    :type result: mediapipe.tasks.python.vision.HandLandmarkerResult
    :return: list of ``(label, (21, 2) array)``.
    :rtype: list[tuple[str, numpy.ndarray]]
    """
    out = []
    for landmarks, handedness in zip(result.hand_landmarks, result.handedness):
        arr = np.array([[lm.x, lm.y] for lm in landmarks], dtype=np.float32)
        out.append((handedness[0].category_name if handedness else "Right", arr))
    return out


class HandsOnlyTracker(BaseTracker):
    """Low-CPU tracker: HandLandmarker only, players split by screen zones."""

    def __init__(self, cfg: TrackingConfig, players: int, hand_model: Path) -> None:
        """Create tracker.

        :param cfg: tracking configuration.
        :type cfg: fruit_knight.config.schema.TrackingConfig
        :param players: number of players (equal horizontal zones).
        :type players: int
        :param hand_model: path of the hand model file.
        :type hand_model: pathlib.Path
        """
        self._players = players
        self._hands = _create_hand_landmarker(hand_model, cfg, MAX_HANDS_PER_PLAYER * players)

    def process(self, rgb, timestamp_ms):
        """Detect hands and assign them to zones.

        :param rgb: contiguous ``uint8`` image of shape ``(H, W, 3)``.
        :type rgb: numpy.ndarray
        :param timestamp_ms: strictly increasing timestamp in milliseconds.
        :type timestamp_ms: int
        :return: hand observations and an empty pose list.
        :rtype: tuple[list[HandObservation], list[PoseObservation]]
        """
        raw = _hand_arrays(self._hands.detect_for_video(_mp_image(rgb), timestamp_ms))
        zones = assign_hands_to_zones([arr[WRIST][0] for _, arr in raw], self._players)
        hands: list[HandObservation] = []
        per_player: dict[int, int] = {}
        for (label, arr), pid in zip(raw, zones):
            if per_player.get(pid, 0) < MAX_HANDS_PER_PLAYER:
                per_player[pid] = per_player.get(pid, 0) + 1
                hands.append(HandObservation(pid, label, arr))
        fix_hand_labels(hands)
        return hands, []

    def close(self) -> None:
        """Release the landmarker."""
        self._hands.close()


class PoseHandsTracker(BaseTracker):
    """Full tracker: PoseLandmarker for mannequins plus HandLandmarker for gestures."""

    def __init__(self, cfg: TrackingConfig, players: int, pose_model: Path, hand_model: Path) -> None:
        """Create tracker.

        :param cfg: tracking configuration.
        :type cfg: fruit_knight.config.schema.TrackingConfig
        :param players: number of players.
        :type players: int
        :param pose_model: path of the pose model file.
        :type pose_model: pathlib.Path
        :param hand_model: path of the hand model file.
        :type hand_model: pathlib.Path
        """
        from mediapipe.tasks.python import BaseOptions, vision

        self._cfg = cfg
        self._players = players
        self._identity = PlayerIdentityTracker(players)
        self._hands = _create_hand_landmarker(hand_model, cfg, MAX_HANDS_PER_PLAYER * players)
        options = vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=pose_model.read_bytes()),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=players,
            min_pose_detection_confidence=cfg.min_detection_confidence,
            min_pose_presence_confidence=cfg.min_detection_confidence,
            min_tracking_confidence=cfg.min_tracking_confidence,
        )
        self._pose = vision.PoseLandmarker.create_from_options(options)

    def process(self, rgb, timestamp_ms):
        """Detect poses and hands, linking each hand to the nearest pose wrist.

        :param rgb: contiguous ``uint8`` image of shape ``(H, W, 3)``.
        :type rgb: numpy.ndarray
        :param timestamp_ms: strictly increasing timestamp in milliseconds.
        :type timestamp_ms: int
        :return: hand and pose observations with player ids.
        :rtype: tuple[list[HandObservation], list[PoseObservation]]
        """
        image = _mp_image(rgb)
        pose_result = self._pose.detect_for_video(image, timestamp_ms)
        raw_hands = _hand_arrays(self._hands.detect_for_video(image, timestamp_ms))

        pose_arrays = [np.array([[lm.x, lm.y] for lm in pose], dtype=np.float32) for pose in pose_result.pose_landmarks]
        centroids = [tuple(((p[LEFT_SHOULDER] + p[RIGHT_SHOULDER]) / 2).tolist()) for p in pose_arrays]
        ids = self._identity.assign(centroids)
        poses = [PoseObservation(pid, arr) for pid, arr in zip(ids, pose_arrays) if pid is not None]

        hand_wrists = [(float(arr[WRIST][0]), float(arr[WRIST][1])) for _, arr in raw_hands]
        if poses:
            pose_wrists = {
                p.player_id: [tuple(p.landmarks[LEFT_WRIST].tolist()), tuple(p.landmarks[RIGHT_WRIST].tolist())]
                for p in poses
            }
            owners = assign_hands_to_poses(hand_wrists, pose_wrists, self._cfg.assign_max_distance)
        else:
            # No body visible: fall back to screen zones so hands stay playable.
            owners = list(assign_hands_to_zones([w[0] for w in hand_wrists], self._players))
        hands = [HandObservation(pid, label, arr) for (label, arr), pid in zip(raw_hands, owners) if pid is not None]
        fix_hand_labels(hands)
        return hands, poses

    def close(self) -> None:
        """Release both landmarkers."""
        self._hands.close()
        self._pose.close()
