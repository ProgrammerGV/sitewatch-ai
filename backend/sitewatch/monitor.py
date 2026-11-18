"""Worker lifecycle and thread-safe presentation of the video pipeline."""

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import cv2

from .capture import FrameSource, LatestFrameCapture
from .config import Settings
from .database import Database
from .domain import EventRules
from .models import Source
from .monitor_state import MonitorPhase, MonitorStatus
from .pipeline import (
    FrameAnalysis,
    FrameAnalyzer,
    FrameSettings,
    OccurrenceRecorder,
    PersonDetector,
)
from .policy import FRAME_WAIT_SECONDS, MAX_FRAME_AGE_SECONDS, WORKER_JOIN_TIMEOUT_SECONDS
from .storage import EventStore
from .vision import YoloDetector

logger = logging.getLogger(__name__)


@dataclass
class SessionResources:
    store: EventStore | None = None
    session_id: UUID | None = None
    capture: FrameSource | None = None
    recorder: OccurrenceRecorder | None = None


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
        self._state_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self._jpeg: bytes | None = None
        self._status = MonitorStatus()
        self.detector: PersonDetector | None = None

    def _publish_status(self, **changes: object) -> None:
        with self._state_lock:
            self._status = self._status.with_changes(**changes)

    def snapshot(self) -> dict:
        with self._state_lock:
            return self._status.model_dump(mode="json")

    def frame(self) -> bytes | None:
        with self._state_lock:
            return self._jpeg

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self, video_file: Path | None = None) -> dict:
        with self.control:
            if self.running:
                return self.snapshot()
            source = self.database.source()
            self.stop_event.clear()
            with self._state_lock:
                self._jpeg = None
                self._status = MonitorStatus(state=MonitorPhase.STARTING)
            self.thread = threading.Thread(
                target=self._run, args=(source, video_file), name="video-analysis", daemon=True
            )
            self.thread.start()
            return self.snapshot()

    def stop(self) -> dict:
        with self.control:
            self.stop_event.set()
            if self.thread:
                self.thread.join(timeout=WORKER_JOIN_TIMEOUT_SECONDS)
            if self.running:
                self._publish_status(state=MonitorPhase.STOPPING)
            return self.snapshot()

    def _run(self, source: Source, video_file: Path | None) -> None:
        resources = SessionResources()
        error = None
        try:
            if self.detector is None:
                self.detector = self.detector_factory(
                    self.settings.absolute(self.settings.model_path), self.settings.model_device
                )
            if self.stop_event.is_set():
                return
            analyzer = self._open_session(source, video_file, resources)
            assert resources.capture is not None and resources.recorder is not None
            self._process_frames(resources.capture, analyzer, resources.recorder)
        except Exception as exc:
            error = (
                str(exc)
                if isinstance(exc, RuntimeError)
                else ("Monitoring failed. Check the application log and database connection.")
            )
            logger.exception("Monitoring interrupted")
        finally:
            self._finish_session(resources, error)

    def _open_session(
        self, source: Source, video_file: Path | None, resources: SessionResources
    ) -> FrameAnalyzer:
        assert self.detector is not None
        resources.store = EventStore(
            self.database,
            self.settings.absolute(self.settings.data_dir),
            self.settings.max_evidence_mb,
        )
        rules = EventRules(
            self.settings.confirmation_window_seconds, self.settings.event_idle_seconds
        )
        configuration = {
            "roi": source.roi,
            "confidence": source.confidence,
            "motion_threshold": source.motion_threshold,
            "inference_fps": self.settings.inference_fps,
            "confirmation_window_seconds": rules.confirmation_window,
            "event_idle_seconds": rules.idle_seconds,
            "input": "file" if video_file else "webcam",
        }
        resources.session_id = resources.store.session_start(
            source, self.detector.version, configuration
        )
        resources.recorder = OccurrenceRecorder(
            resources.store, rules, resources.session_id, source.roi
        )
        self._publish_status(session_id=str(resources.session_id))
        resources.capture = self.capture_factory(source.camera_index, video_file)
        self._publish_status(state=MonitorPhase.RUNNING, warming_up=True)
        frame_settings = FrameSettings(
            region=tuple(source.roi),
            confidence=source.confidence,
            motion_threshold=source.motion_threshold,
            warmup_seconds=self.settings.motion_warmup_seconds,
        )
        return FrameAnalyzer(self.detector, frame_settings)

    def _process_frames(
        self, capture: FrameSource, analyzer: FrameAnalyzer, recorder: OccurrenceRecorder
    ) -> None:
        previous_sequence = -1
        processed_frames = 0
        beginning = time.monotonic()
        while not self.stop_event.is_set():
            started = time.monotonic()
            packet = capture.snapshot()
            if capture.finished:
                break
            if capture.error:
                raise RuntimeError(capture.error)
            if packet is None or packet.sequence == previous_sequence:
                last_capture = packet.captured_at if packet else beginning
                if started - last_capture > MAX_FRAME_AGE_SECONDS:
                    raise RuntimeError("No fresh image for more than two seconds.")
                self.stop_event.wait(FRAME_WAIT_SECONDS)
                continue
            previous_sequence, captured_at, image = packet
            result = analyzer.analyze(image, captured_at)
            recorder.record(result)
            processed_frames += 1
            self._publish_analysis(result, recorder, processed_frames, beginning)
            remaining = 1 / self.settings.inference_fps - (time.monotonic() - started)
            self.stop_event.wait(max(0, remaining))

    def _publish_analysis(
        self,
        frame: FrameAnalysis,
        recorder: OccurrenceRecorder,
        processed_frames: int,
        beginning: float,
    ) -> None:
        ok, encoded = cv2.imencode(".jpg", frame.annotated)
        if not ok:
            raise RuntimeError("Preview JPEG encoding failed.")
        with self._state_lock:
            self._jpeg = encoded.tobytes()
        self._publish_status(
            people=len(frame.detections),
            people_in_region=len(frame.people_in_region),
            motion=frame.motion_detected,
            motion_score=round(frame.motion_score, 4),
            warming_up=not frame.background_ready,
            inference_ms=round(frame.inference_ms, 1),
            frame_age_ms=round(frame.frame_age_ms, 1),
            processed_frames=processed_frames,
            analysis_fps=round(processed_frames / max(frame.processed_at - beginning, 0.001), 2),
            occurrence_id=str(recorder.event_id) if recorder.event_id else None,
            person_confirmed=recorder.person_confirmed,
        )

    def _finish_session(self, resources: SessionResources, error: str | None) -> None:
        if resources.capture:
            try:
                resources.capture.close()
            except Exception:
                logger.exception("Capture cleanup failed")
                error = error or "Unable to release capture cleanly. Check the application log."
        try:
            if resources.recorder:
                resources.recorder.interrupt(failed=error is not None)
            if resources.store and resources.session_id:
                resources.store.session_end(resources.session_id, error)
        except Exception:
            logger.exception("Could not finalize session; startup reconciliation will recover it")
            error = error or "Unable to finalize monitoring in PostgreSQL. Check the connection."
        self._publish_status(
            state=MonitorPhase.ERROR if error else MonitorPhase.IDLE,
            error=error,
            occurrence_id=None,
            people=0,
            people_in_region=0,
            motion=False,
            warming_up=False,
            person_confirmed=False,
        )
