import logging
import threading
import time
from pathlib import Path
from uuid import UUID

import cv2

from .config import Settings
from .database import Database
from .domain import EventRules
from .storage import EventStore
from .vision import MotionDetector, YoloDetector, annotate, serialized

logger = logging.getLogger(__name__)


class LatestFrameCapture:
    """A bounded, latest-only frame slot; analysis can never build an old-frame queue."""

    def __init__(self, camera_index: int, video_file: Path | None = None):
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.latest = None
        self.sequence = 0
        self.error: str | None = None
        self.video_file = video_file
        if video_file:
            self.cap = cv2.VideoCapture(str(video_file))
        else:
            self.cap = (
                cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                if __import__("os").name == "nt"
                else cv2.VideoCapture(camera_index)
            )
        if not self.cap.isOpened():
            self.cap.release()
            raise RuntimeError(
                "Cannot open webcam. Check permissions, camera index, and other applications."
            )
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.thread = threading.Thread(target=self._read, name="camera-capture", daemon=True)
        self.thread.start()

    def _read(self):
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 25
        try:
            while not self.stop_event.is_set():
                ok, frame = self.cap.read()
                if not ok:
                    self.error = (
                        "Video ended."
                        if self.video_file
                        else "Webcam disconnected or frame capture failed."
                    )
                    return
                with self.lock:
                    self.sequence += 1
                    self.latest = (self.sequence, time.monotonic(), frame)
                self.stop_event.wait(1 / max(fps, 1) if self.video_file else 0.005)
        except Exception:
            logger.exception("Capture failed")
            self.error = "Frame capture failed. See the application log."
        finally:
            self.cap.release()

    def snapshot(self):
        with self.lock:
            return self.latest

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=3)


class Monitor:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        detector_factory=YoloDetector,
        capture_factory=LatestFrameCapture,
    ):
        self.settings, self.database = settings, database
        self.detector_factory, self.capture_factory = detector_factory, capture_factory
        self.control = threading.RLock()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.jpeg: bytes | None = None
        self.status = {
            "state": "idle",
            "error": None,
            "people": 0,
            "people_in_region": 0,
            "motion": False,
            "motion_score": 0,
            "warming_up": False,
            "inference_ms": 0,
            "frame_age_ms": 0,
            "processed_frames": 0,
            "analysis_fps": 0,
            "session_id": None,
            "occurrence_id": None,
        }
        self.detector = None

    def _set(self, **values):
        with self.lock:
            self.status.update(values)

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.status)

    def frame(self) -> bytes | None:
        with self.lock:
            return self.jpeg

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, video_file: Path | None = None) -> dict:
        with self.control:
            if self.running:
                return self.snapshot()
            source = self.database.source()
            self.stop_event.clear()
            self.jpeg = None
            self._set(
                state="starting",
                error=None,
                processed_frames=0,
                session_id=None,
                occurrence_id=None,
                people=0,
                people_in_region=0,
                motion=False,
                analysis_fps=0,
                inference_ms=0,
                frame_age_ms=0,
            )
            self.thread = threading.Thread(
                target=self._run, args=(source, video_file), name="video-analysis", daemon=True
            )
            self.thread.start()
            return self.snapshot()

    def stop(self) -> dict:
        with self.control:
            self.stop_event.set()
            if self.thread:
                self.thread.join(timeout=8)
            if self.running:
                self._set(state="stopping")
            return self.snapshot()

    def _run(self, source, video_file):
        capture = None
        session_id: UUID | None = None
        event_id: UUID | None = None
        rules = EventRules(
            self.settings.confirmation_window_seconds, self.settings.event_idle_seconds
        )
        store = None
        error = None
        try:
            store = EventStore(
                self.database,
                self.settings.absolute(self.settings.data_dir),
                self.settings.max_evidence_mb,
            )
            if self.detector is None:
                self.detector = self.detector_factory(
                    self.settings.absolute(self.settings.model_path), self.settings.model_device
                )
            if self.stop_event.is_set():
                return
            configuration = {
                "roi": source.roi,
                "confidence": source.confidence,
                "motion_threshold": source.motion_threshold,
                "inference_fps": self.settings.inference_fps,
                "confirmation_window_seconds": rules.confirmation_window,
                "event_idle_seconds": rules.idle_seconds,
                "input": "file" if video_file else "webcam",
            }
            session_id = store.session_start(source, self.detector.version, configuration)
            self._set(session_id=str(session_id))
            capture = self.capture_factory(source.camera_index, video_file)
            motion = MotionDetector(self.settings.motion_warmup_seconds)
            self._set(state="running", warming_up=True)
            previous_sequence = -1
            last_observation = float("-inf")
            evidence_score = -1
            frames = 0
            beginning = time.monotonic()
            while not self.stop_event.is_set():
                started = time.monotonic()
                packet = capture.snapshot()
                if capture.error:
                    if capture.error == "Video ended.":
                        break
                    raise RuntimeError(capture.error)
                if packet is None or packet[0] == previous_sequence:
                    if started - (packet[1] if packet else beginning) > 2:
                        raise RuntimeError("No fresh image for more than two seconds.")
                    self.stop_event.wait(0.02)
                    continue
                previous_sequence, captured, image = packet
                if started - captured > 2:
                    raise RuntimeError("Captured image is stale; monitoring was stopped.")
                score, warmed = motion.score(image, source.roi)
                detections = self.detector.detect(image, source.confidence)
                now = time.monotonic()
                if now - captured > 2:
                    raise RuntimeError(
                        "Analysis took too long; the image is stale. Monitoring was stopped."
                    )
                in_region = [d for d in detections if d.in_region(tuple(source.roi))]
                moved = warmed and score >= source.motion_threshold
                opened, closed = rules.step(now, moved, len(in_region))
                view = annotate(image, detections, source.roi)
                if opened:
                    event_id = store.event_open(session_id)
                    evidence_score, last_observation = -1, float("-inf")
                if event_id is not None and rules.state is not None:
                    current_score = max((d.confidence for d in in_region), default=0)
                    if current_score > evidence_score:
                        store.evidence(event_id, image, view)
                        evidence_score = current_score
                    # Persist at most 1 Hz, plus the first human confirmation transition.
                    just_confirmed = rules.state.person_confirmed and not self.snapshot().get(
                        "person_confirmed", False
                    )
                    if now - last_observation >= 1 or just_confirmed:
                        store.observation(
                            event_id, score, len(in_region), serialized(detections, source.roi)
                        )
                        store.update(event_id, rules.state)
                        last_observation = now
                    if closed:
                        store.update(event_id, rules.state, close=True)
                        event_id = None
                        rules.reset()
                ok, encoded = cv2.imencode(".jpg", view)
                if not ok:
                    raise RuntimeError("Preview JPEG encoding failed.")
                frames += 1
                with self.lock:
                    self.jpeg = encoded.tobytes()
                self._set(
                    people=len(detections),
                    people_in_region=len(in_region),
                    motion=moved,
                    motion_score=round(score, 4),
                    warming_up=not warmed,
                    inference_ms=round((now - started) * 1000, 1),
                    frame_age_ms=round((now - captured) * 1000, 1),
                    processed_frames=frames,
                    analysis_fps=round(frames / max(now - beginning, 0.001), 2),
                    occurrence_id=str(event_id) if event_id else None,
                    person_confirmed=bool(rules.state and rules.state.person_confirmed),
                )
                self.stop_event.wait(
                    max(0, 1 / self.settings.inference_fps - (time.monotonic() - started))
                )
        except Exception as exc:
            error = (
                str(exc)
                if isinstance(exc, RuntimeError)
                else "Monitoring failed. Check the application log and database connection."
            )
            logger.exception("Monitoring interrupted")
            if rules.state:
                rules.state.failed = True
        finally:
            if capture:
                capture.close()
            try:
                if store and event_id and rules.state:
                    store.update(event_id, rules.state, close=True, interrupted=True)
                if store and session_id:
                    store.session_end(session_id, error)
            except Exception:
                logger.exception(
                    "Could not finalize session; startup reconciliation will recover it"
                )
                error = (
                    error or "Unable to finalize monitoring in PostgreSQL. Check the connection."
                )
            self._set(
                state="error" if error else "idle",
                error=error,
                occurrence_id=None,
                people=0,
                people_in_region=0,
                motion=False,
                warming_up=False,
                person_confirmed=False,
            )
