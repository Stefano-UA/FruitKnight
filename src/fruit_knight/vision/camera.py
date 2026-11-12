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
# Seconds a single backend may take to open and deliver its first frame.
OPEN_TIMEOUT_S = 6.0


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

    def _try_backend(self, index: int, backend: int, result: list) -> None:
        """Open one backend and verify it delivers a frame (runs in a helper thread).

        :param index: camera device index.
        :type index: int
        :param backend: OpenCV backend constant.
        :type backend: int
        :param result: list receiving the working capture, if any.
        :type result: list
        """
        cap = cv2.VideoCapture(index, backend)
        if not cap.isOpened():
            cap.release()
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._cfg.request_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._cfg.request_height)
        cap.set(cv2.CAP_PROP_FPS, self._cfg.request_fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        ok, _ = cap.read()
        if ok:
            result.append(cap)
        else:
            cap.release()

    def _open(self, index: int) -> cv2.VideoCapture | None:
        """Open a camera trying several backends, each with a time limit.

        Windows drivers can block inside ``VideoCapture``; a backend that does not answer in time is
        abandoned and the next one is tried.

        :param index: camera device index.
        :type index: int
        :return: opened capture or ``None``.
        :rtype: cv2.VideoCapture | None
        """
        if sys.platform.startswith("win"):
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]
        for backend in backends:
            result: list = []
            worker = threading.Thread(target=self._try_backend, args=(index, backend, result), daemon=True)
            worker.start()
            worker.join(timeout=OPEN_TIMEOUT_S)
            if result:
                log.info("Camera %d opened with backend %d", index, backend)
                return result[0]
            log.warning("Camera %d: backend %d failed or timed out", index, backend)
            if self._stop.is_set():
                break
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
