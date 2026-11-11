"""Vision pipeline: mirror, ROI crop and tracking executed off the main thread."""

from __future__ import annotations

import logging
import threading
import time

import cv2
import numpy as np

from fruit_knight.config.schema import TrackingConfig
from fruit_knight.utils.constants import TrackingMode
from fruit_knight.vision.camera import STATUS_READY, CameraCapture
from fruit_knight.vision.models import ensure_models
from fruit_knight.vision.roi import RoiRect
from fruit_knight.vision.trackers import BaseTracker, HandsOnlyTracker, PoseHandsTracker, TrackingResult

log = logging.getLogger(__name__)


class VisionPipeline:
    """Owns the camera and a worker thread that publishes ``TrackingResult`` objects."""

    def __init__(self, cfg: TrackingConfig) -> None:
        """Create idle pipeline.

        :param cfg: tracking configuration.
        :type cfg: fruit_knight.config.schema.TrackingConfig
        """
        self._cfg = cfg
        self.camera = CameraCapture(cfg.camera)
        self._roi = RoiRect.full()
        self._mode = TrackingMode.POSE_HANDS
        self._players = 1
        self._tracking_wanted = False
        self._tracker_dirty = False
        self._tracker: BaseTracker | None = None
        self._result: TrackingResult | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.tracker_status = "off"
        self.error = ""

    # ------------------------------------------------------------------ camera
    def start_camera(self, index: int) -> None:
        """Open a camera device.

        :param index: camera device index.
        :type index: int
        """
        self.camera.start(index)

    def preview_frame(self) -> np.ndarray | None:
        """Fetch newest mirrored full-frame RGB image for the calibration screen.

        :return: RGB image or ``None`` when no frame arrived yet.
        :rtype: numpy.ndarray | None
        """
        frame, _ = self.camera.read_latest()
        if frame is None:
            return None
        return cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)

    @property
    def camera_ready(self) -> bool:
        """Report camera health.

        :return: True when frames are streaming.
        :rtype: bool
        """
        return self.camera.status == STATUS_READY

    # ---------------------------------------------------------------- tracking
    def set_roi(self, roi: RoiRect) -> None:
        """Select play area applied before tracking.

        :param roi: normalised crop rectangle.
        :type roi: fruit_knight.vision.roi.RoiRect
        """
        self._roi = roi

    def start_tracking(self, mode: TrackingMode, players: int) -> None:
        """Enable processing with the chosen tracker.

        :param mode: tracking pipeline to use.
        :type mode: fruit_knight.utils.constants.TrackingMode
        :param players: number of players.
        :type players: int
        """
        self._mode, self._players = mode, players
        self._tracking_wanted = True
        self._tracker_dirty = True
        self.tracker_status = "loading"
        self.error = ""
        with self._lock:
            self._result = None
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True, name="vision-worker")
            self._thread.start()

    def stop_tracking(self) -> None:
        """Disable processing and stop the worker thread."""
        self._tracking_wanted = False
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        self._drop_tracker()
        self.tracker_status = "off"

    def latest(self) -> TrackingResult | None:
        """Fetch newest processed frame.

        :return: latest result or ``None`` before the first frame.
        :rtype: fruit_knight.vision.trackers.TrackingResult | None
        """
        with self._lock:
            return self._result

    def shutdown(self) -> None:
        """Stop worker and camera."""
        self.stop_tracking()
        self.camera.stop()

    # ---------------------------------------------------------------- internals
    def _drop_tracker(self) -> None:
        """Close and forget the current tracker."""
        if self._tracker is not None:
            try:
                self._tracker.close()
            except Exception:  # noqa: BLE001 - native teardown must never crash the game
                log.exception("Tracker close failed")
            self._tracker = None

    def _build_tracker(self) -> None:
        """Create the tracker for the requested mode, downloading models if needed."""
        self._drop_tracker()
        try:
            paths = ensure_models(self._cfg, need_pose=self._mode == TrackingMode.POSE_HANDS)
            if self._mode == TrackingMode.POSE_HANDS:
                self._tracker = PoseHandsTracker(self._cfg, self._players, paths["pose"], paths["hand"])
            else:
                self._tracker = HandsOnlyTracker(self._cfg, self._players, paths["hand"])
            self.tracker_status = "ready"
        except Exception as exc:  # noqa: BLE001 - report any model/native failure in the UI
            log.exception("Tracker creation failed")
            self.error = str(exc)
            self.tracker_status = "error"

    def _downscale(self, rgb: np.ndarray) -> np.ndarray:
        """Shrink large frames for faster inference.

        :param rgb: RGB frame.
        :type rgb: numpy.ndarray
        :return: frame whose longest side is at most ``max_inference_side``.
        :rtype: numpy.ndarray
        """
        side = max(rgb.shape[:2])
        if side <= self._cfg.max_inference_side:
            return rgb
        scale = self._cfg.max_inference_side / side
        return cv2.resize(rgb, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    def _run(self) -> None:
        """Worker loop: fetch frame, crop, track, publish."""
        last_counter = 0
        last_ts = 0
        while not self._stop.is_set():
            if self._tracker_dirty:
                self._tracker_dirty = False
                self._build_tracker()
            frame, counter = self.camera.read_latest()
            if frame is None or counter == last_counter:
                time.sleep(0.004)
                continue
            last_counter = counter
            rgb = cv2.cvtColor(self._roi.crop(cv2.flip(frame, 1)), cv2.COLOR_BGR2RGB)
            rgb = np.ascontiguousarray(rgb)
            hands, poses = [], []
            if self._tracker is not None:
                last_ts = max(last_ts + 1, int(time.monotonic() * 1000))
                try:
                    hands, poses = self._tracker.process(self._downscale(rgb), last_ts)
                except Exception:  # noqa: BLE001 - keep streaming video if one inference fails
                    log.exception("Inference failed")
            with self._lock:
                self._result = TrackingResult(rgb, hands, poses, time.monotonic())
