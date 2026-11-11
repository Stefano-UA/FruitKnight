"""Tests for gesture rules, player assignment, ROI and trackers."""

from __future__ import annotations

import numpy as np
import pytest

from fruit_knight.config import load_config
from fruit_knight.utils.constants import HandState, TrackingMode
from fruit_knight.vision.gestures import GestureClassifier, StateDebouncer
from fruit_knight.vision.hands import HandTracker
from fruit_knight.vision.models import missing_models
from fruit_knight.vision.roi import RoiRect
from fruit_knight.vision.trackers import (
    HandObservation,
    PlayerIdentityTracker,
    assign_hands_to_poses,
    assign_hands_to_zones,
)

CFG = load_config()


def make_hand(extended: list[bool], spread: float = 0.1) -> np.ndarray:
    """Build synthetic landmarks of a hand pointing up (y grows downward).

    :param extended: extension flag for index, middle, ring and pinky.
    :type extended: list[bool]
    :param spread: lateral offset between adjacent fingers relative to palm size.
    :type spread: float
    :return: array of shape ``(21, 2)``.
    :rtype: numpy.ndarray
    """
    pts = np.zeros((21, 2), dtype=np.float32)
    pts[0] = (0.0, 0.0)  # wrist
    for i, (mcp, pip, tip) in enumerate([(5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20)]):
        x = (i - 1.5) * spread
        pts[mcp] = (x, -1.0)
        pts[pip] = (x, -1.5)
        pts[tip] = (x, -2.2) if extended[i] else (x, -0.6)
    return pts


def test_knife_open_fist_classification() -> None:
    """Posture rules follow the specification."""
    clf = GestureClassifier(CFG.gestures)
    assert clf.classify(make_hand([True] * 4, spread=0.1)) == HandState.KNIFE_HAND
    assert clf.classify(make_hand([True] * 4, spread=0.6)) == HandState.OPEN_PALM
    assert clf.classify(make_hand([False] * 4)) == HandState.CLOSED_FIST
    assert clf.classify(make_hand([True, True, False, False])) == HandState.UNKNOWN


def test_debouncer_needs_consecutive_frames() -> None:
    """Single-frame flicker is ignored and UNKNOWN keeps the previous posture."""
    deb = StateDebouncer(2)
    assert deb.update(HandState.OPEN_PALM) == HandState.UNKNOWN
    assert deb.update(HandState.OPEN_PALM) == HandState.OPEN_PALM
    assert deb.update(HandState.CLOSED_FIST) == HandState.OPEN_PALM
    assert deb.update(HandState.UNKNOWN) == HandState.OPEN_PALM
    assert deb.update(HandState.CLOSED_FIST) == HandState.OPEN_PALM
    assert deb.update(HandState.CLOSED_FIST) == HandState.CLOSED_FIST


def test_zone_and_pose_assignment() -> None:
    """Hands map to horizontal zones and to the nearest pose wrists."""
    assert assign_hands_to_zones([0.1, 0.49, 0.51, 0.99], 2) == [1, 1, 2, 2]
    owners = assign_hands_to_poses(
        [(0.2, 0.5), (0.8, 0.5), (0.9, 0.9)],
        {1: [(0.25, 0.5), (0.1, 0.5)], 2: [(0.75, 0.5), (0.9, 0.5)]},
        0.3,
    )
    assert owners[:2] == [1, 2]


def test_identity_tracker_is_stable() -> None:
    """Ids follow bodies when they move and when order changes."""
    ident = PlayerIdentityTracker(2)
    assert ident.assign([(0.7, 0.4), (0.2, 0.4)]) == [2, 1]
    assert ident.assign([(0.25, 0.4), (0.68, 0.4)]) == [1, 2]


def test_roi_crop_and_clamp() -> None:
    """ROI clamps to the frame and crops arrays."""
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    roi = RoiRect.from_corners(0.5, 0.5, 0.0, 0.0)
    assert roi.crop(frame).shape[:2] == (50, 100)
    assert RoiRect.from_corners(0.1, 0.1, 0.12, 0.12).is_full


def test_hand_tracker_velocity_and_state() -> None:
    """HandTracker emits viewport-space samples with velocity."""
    tracker = HandTracker(CFG.gestures, (1280, 720))
    lm = make_hand([True] * 4) * 0.05 + 0.5
    sample = {}
    for i in range(6):
        sample = tracker.update([HandObservation(1, "Right", lm + i * 0.01)], (640, 480), i / 30)
    hand = sample["p1:Right"]
    assert hand.state == HandState.KNIFE_HAND
    assert hand.velocity[0] > 100


@pytest.mark.skipif(bool(missing_models(CFG.tracking)), reason="MediaPipe models not downloaded")
@pytest.mark.parametrize("mode", [TrackingMode.POSE_HANDS, TrackingMode.HANDS_ONLY])
def test_mediapipe_trackers_run_on_blank_frame(mode: TrackingMode) -> None:
    """Both trackers initialise and process an empty image without errors."""
    from fruit_knight.vision.models import ensure_models
    from fruit_knight.vision.trackers import HandsOnlyTracker, PoseHandsTracker

    paths = ensure_models(CFG.tracking, need_pose=True)
    if mode == TrackingMode.POSE_HANDS:
        tracker = PoseHandsTracker(CFG.tracking, 2, paths["pose"], paths["hand"])
    else:
        tracker = HandsOnlyTracker(CFG.tracking, 2, paths["hand"])
    blank = np.zeros((240, 320, 3), dtype=np.uint8)
    for ts in (1, 34, 67):
        hands, poses = tracker.process(blank, ts)
        assert hands == [] and poses == []
    tracker.close()


@pytest.mark.skipif(bool(missing_models(CFG.tracking)), reason="MediaPipe models not downloaded")
def test_pipeline_mirrors_crops_and_tracks_synthetic_frames() -> None:
    """Injected frames flow through mirror, ROI crop and the tracker thread."""
    import time

    from fruit_knight.vision.camera import STATUS_READY
    from fruit_knight.vision.pipeline import VisionPipeline

    pipeline = VisionPipeline(CFG.tracking)
    frame = np.zeros((120, 200, 3), dtype=np.uint8)
    frame[:, :100] = (255, 0, 0)  # left half blue in BGR; becomes the right half after mirroring
    pipeline.camera.status = STATUS_READY
    pipeline.set_roi(RoiRect(0.5, 0.0, 0.5, 1.0))
    pipeline.start_tracking(TrackingMode.HANDS_ONLY, 1)
    try:
        result = None
        for i in range(400):
            pipeline.camera._frame, pipeline.camera._counter = frame.copy(), i + 1
            result = pipeline.latest()
            if result is not None and pipeline.tracker_status == "ready":
                break
            time.sleep(0.02)
        assert result is not None and pipeline.tracker_status == "ready"
        assert result.frame.shape == (120, 100, 3)
        assert result.frame[0, 0].tolist() == [0, 0, 255]  # mirrored, cropped and converted to RGB
    finally:
        pipeline.shutdown()
