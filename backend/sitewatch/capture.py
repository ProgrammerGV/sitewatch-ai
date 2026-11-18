"""Camera acquisition with a bounded latest-frame buffer."""

import logging
import os
import threading
import time
from pathlib import Path
from typing import NamedTuple, Protocol

import cv2
import numpy as np

from .policy import (
    CAPTURE_HEIGHT,
    CAPTURE_JOIN_TIMEOUT_SECONDS,
    CAPTURE_POLL_SECONDS,
    CAPTURE_WIDTH,
)

logger = logging.getLogger(__name__)


class FramePacket(NamedTuple):
    sequence: int
    captured_at: float
    image: np.ndarray


class FrameSource(Protocol):
    error: str | None
    finished: bool

    def snapshot(self) -> FramePacket | None: ...

    def close(self) -> None: ...


class LatestFrameCapture:
    """A bounded, latest-only frame slot; analysis can never build an old-frame queue."""

    def __init__(self, camera_index: int, video_file: Path | None = None):
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.latest: FramePacket | None = None
        self.sequence = 0
        self.error: str | None = None
        self.finished = False
        self.video_file = video_file
        if video_file:
            self.cap = cv2.VideoCapture(str(video_file))
        else:
            self.cap = (
                cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                if os.name == "nt"
                else cv2.VideoCapture(camera_index)
            )
        if not self.cap.isOpened():
            self.cap.release()
            raise RuntimeError(
                "Cannot open webcam. Check permissions, camera index, and other applications."
            )
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
        self.thread = threading.Thread(target=self._read, name="camera-capture", daemon=True)
        self.thread.start()

    def _read(self):
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 25
        try:
            while not self.stop_event.is_set():
                ok, frame = self.cap.read()
                if not ok:
                    self.finished = self.video_file is not None
                    self.error = (
                        None if self.finished else "Webcam disconnected or frame capture failed."
                    )
                    return
                with self.lock:
                    self.sequence += 1
                    self.latest = FramePacket(self.sequence, time.monotonic(), frame)
                self.stop_event.wait(1 / max(fps, 1) if self.video_file else CAPTURE_POLL_SECONDS)
        except Exception:
            logger.exception("Capture failed")
            self.error = "Frame capture failed. See the application log."
        finally:
            self.cap.release()

    def snapshot(self) -> FramePacket | None:
        with self.lock:
            return self.latest

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=CAPTURE_JOIN_TIMEOUT_SECONDS)
