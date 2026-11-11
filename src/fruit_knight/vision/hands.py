"""Game-facing hand model: posture, palm position and velocity per tracked hand."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from fruit_knight.config.schema import GestureConfig
from fruit_knight.utils.constants import MIDDLE_TIP, PALM_LANDMARKS, WRIST, HandState
from fruit_knight.vision.gestures import GestureClassifier, StateDebouncer
from fruit_knight.vision.motion import VelocityEstimator
from fruit_knight.vision.trackers import HandObservation

Vec = tuple[float, float]
# Seconds a hand may vanish before its filters are discarded.
FORGET_AFTER_S = 1.0


@dataclass
class HandSample:
    """Snapshot of one hand in viewport coordinates."""

    key: str
    player_id: int
    state: HandState
    palm: Vec
    tip: Vec
    wrist: Vec
    velocity: Vec
    landmarks: np.ndarray | None = None  # (21, 2) viewport pixels, for drawing
    synthetic: bool = False


class _HandFilters:
    """Per-hand temporal filters."""

    def __init__(self, cfg: GestureConfig) -> None:
        """Create filters.

        :param cfg: gesture configuration.
        :type cfg: fruit_knight.config.schema.GestureConfig
        """
        self.debouncer = StateDebouncer(cfg.debounce_frames)
        self.velocity = VelocityEstimator(cfg.velocity_window_s, cfg.velocity_smoothing)
        self.last_seen = 0.0


class HandTracker:
    """Turns raw observations into stable ``HandSample`` objects."""

    def __init__(self, cfg: GestureConfig, viewport: tuple[int, int]) -> None:
        """Create tracker.

        :param cfg: gesture configuration.
        :type cfg: fruit_knight.config.schema.GestureConfig
        :param viewport: game viewport size in pixels.
        :type viewport: tuple[int, int]
        """
        self._cfg = cfg
        self._viewport = np.array(viewport, dtype=np.float32)
        self._classifier = GestureClassifier(cfg)
        self._filters: dict[str, _HandFilters] = {}

    def update(self, observations: list[HandObservation], frame_size: tuple[int, int], now: float) -> dict[str, HandSample]:
        """Process observations of one frame.

        :param observations: hands detected in the processed frame.
        :type observations: list[fruit_knight.vision.trackers.HandObservation]
        :param frame_size: processed frame width and height in pixels.
        :type frame_size: tuple[int, int]
        :param now: current time in seconds.
        :type now: float
        :return: samples keyed by ``"p<id>:<label>"``.
        :rtype: dict[str, HandSample]
        """
        samples: dict[str, HandSample] = {}
        frame_wh = np.array(frame_size, dtype=np.float32)
        for obs in observations:
            key = f"p{obs.player_id}:{obs.label}"
            filt = self._filters.get(key)
            if filt is None or now - filt.last_seen > FORGET_AFTER_S:
                filt = self._filters[key] = _HandFilters(self._cfg)
            filt.last_seen = now
            # Classify in frame pixels so ratios stay aspect-correct after ROI cropping.
            state = filt.debouncer.update(self._classifier.classify(obs.landmarks * frame_wh))
            pts = obs.landmarks * self._viewport  # stretched to the viewport
            palm = tuple(pts[list(PALM_LANDMARKS)].mean(axis=0).tolist())
            velocity = filt.velocity.push(now, palm)
            samples[key] = HandSample(
                key=key,
                player_id=obs.player_id,
                state=state,
                palm=palm,
                tip=tuple(pts[MIDDLE_TIP].tolist()),
                wrist=tuple(pts[WRIST].tolist()),
                velocity=velocity,
                landmarks=pts,
            )
        for key in [k for k, f in self._filters.items() if now - f.last_seen > FORGET_AFTER_S * 3]:
            del self._filters[key]
        return samples
