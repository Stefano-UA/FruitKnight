"""Threaded webcam capture that always exposes the newest frame."""

from __future__ import annotations

import logging
import sys
import threading
import time

import cv2
import numpy as np

from fruit_knight.config.schema import CameraConfig

log = logging.getLogger(__name__)

STATUS_CLOSED = "closed"
STATUS_OPENING = "opening"
STATUS_READY = "ready"
STATUS_FAILED = "failed"
# Consecutive failed reads tolerated before the stream is declared dead.
MAX_READ_FAILURES = 120


class CameraCapture:
    """Background reader around ``cv2.VideoCapture``."""

    def __init__(self, cfg: CameraConfig) -> None:
        """Create idle capture.

        :param cfg: camera request settings.
        :type cfg: fruit_knight.config.schema.CameraConfig
        """
        self._cfg = cfg
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._counter = 0
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.status = STATUS_CLOSED
        self.index = cfg.default_index

    def _open(self, index: int) -> cv2.VideoCapture | None:
        """Open a camera device, preferring DirectShow on Windows.

        :param index: camera device index.
        :type index: int
        :return: opened capture or ``None``.
        :rtype: cv2.VideoCapture | None
        """
        backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if sys.platform.startswith("win") else [cv2.CAP_ANY]
        for backend in backends:
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._cfg.request_width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._cfg.request_height)
                cap.set(cv2.CAP_PROP_FPS, self._cfg.request_fps)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return cap
            cap.release()
        return None

    def _run(self, index: int) -> None:
        """Capture loop executed in the worker thread.

        :param index: camera device index.
        :type index: int
        """
        cap = self._open(index)
        if cap is None:
            log.warning("Camera %d could not be opened", index)
            self.status = STATUS_FAILED
            return
        self.status = STATUS_READY
        failures = 0
        while not self._stop.is_set():
            ok, frame = cap.read()
            if ok and frame is not None:
                failures = 0
                with self._lock:
                    self._frame = frame
                    self._counter += 1
            else:
                failures += 1
                time.sleep(0.01)
                if failures > MAX_READ_FAILURES:
                    self.status = STATUS_FAILED
                    break
        cap.release()

    def start(self, index: int) -> None:
        """Start (or restart) capture on a device without blocking the caller.

        :param index: camera device index.
        :type index: int
        """
        self.stop()
        self.index = index
        self._stop.clear()
        self.status = STATUS_OPENING
        self._thread = threading.Thread(target=self._run, args=(index,), daemon=True, name="camera-capture")
        self._thread.start()

    def stop(self) -> None:
        """Stop capture and release the device."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        with self._lock:
            self._frame, self._counter = None, 0
        self.status = STATUS_CLOSED

    def read_latest(self) -> tuple[np.ndarray | None, int]:
        """Fetch newest BGR frame.

        :return: frame (or ``None``) and a counter that increases with every new frame.
        :rtype: tuple[numpy.ndarray | None, int]
        """
        with self._lock:
            return self._frame, self._counter
