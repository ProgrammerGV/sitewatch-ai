"""Frame analysis and occurrence recording, independent of the web/UI status."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import numpy as np

from .domain import Detection, EventRules, EventState
from .policy import MAX_FRAME_AGE_SECONDS, OBSERVATION_INTERVAL_SECONDS
from .vision import MotionDetector, annotate, serialized


class PersonDetector(Protocol):
    version: str

    def detect(self, image: np.ndarray, confidence: float) -> list[Detection]: ...


class OccurrencePersistence(Protocol):
    def event_open(self, session_id: UUID) -> UUID: ...

    def evidence(self, event_id: UUID, original: np.ndarray, annotated: np.ndarray) -> None: ...

    def observation(
        self, event_id: UUID, score: float, people: int, detections: list[dict]
    ) -> None: ...

    def update(
        self, event_id: UUID, state: EventState, *, close: bool = False, interrupted: bool = False
    ) -> None: ...


@dataclass(frozen=True)
class FrameSettings:
    region: tuple[float, float, float, float]
    confidence: float
    motion_threshold: float
    warmup_seconds: float


@dataclass(frozen=True)
class FrameAnalysis:
    image: np.ndarray
    annotated: np.ndarray
    detections: list[Detection]
    people_in_region: list[Detection]
    motion_score: float
    motion_detected: bool
    background_ready: bool
    captured_at: float
    processed_at: float
    inference_ms: float

    @property
    def frame_age_ms(self) -> float:
        return (self.processed_at - self.captured_at) * 1000


class FrameAnalyzer:
    def __init__(
        self,
        detector: PersonDetector,
        settings: FrameSettings,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.detector = detector
        self.clock = clock
        self.region = settings.region
        self.confidence = settings.confidence
        self.motion_threshold = settings.motion_threshold
        self.motion = MotionDetector(settings.warmup_seconds)

    def analyze(self, image: np.ndarray, captured_at: float) -> FrameAnalysis:
        started = self.clock()
        if started - captured_at > MAX_FRAME_AGE_SECONDS:
            raise RuntimeError("Captured image is stale; monitoring was stopped.")
        score, background_ready = self.motion.score(image, list(self.region))
        detections = self.detector.detect(image, self.confidence)
        processed_at = self.clock()
        if processed_at - captured_at > MAX_FRAME_AGE_SECONDS:
            raise RuntimeError(
                "Analysis took too long; the image is stale. Monitoring was stopped."
            )
        return FrameAnalysis(
            image=image,
            annotated=annotate(image, detections, list(self.region)),
            detections=detections,
            people_in_region=[d for d in detections if d.in_region(self.region)],
            motion_score=score,
            motion_detected=background_ready and score >= self.motion_threshold,
            background_ready=background_ready,
            captured_at=captured_at,
            processed_at=processed_at,
            inference_ms=(processed_at - started) * 1000,
        )


class OccurrenceRecorder:
    """Translate rule transitions into persistence, without reading presentation state."""

    def __init__(
        self, store: OccurrencePersistence, rules: EventRules, session_id: UUID, region: list[float]
    ):
        self.store, self.rules = store, rules
        self.session_id, self.region = session_id, region
        self.event_id: UUID | None = None
        self._last_observation = float("-inf")
        self._best_evidence_score = -1.0

    @property
    def person_confirmed(self) -> bool:
        return bool(self.rules.state and self.rules.state.person_confirmed)

    def record(self, frame: FrameAnalysis) -> None:
        previously_confirmed = self.person_confirmed
        transition = self.rules.step(
            frame.processed_at, frame.motion_detected, len(frame.people_in_region)
        )
        if transition.opened:
            self.event_id = self.store.event_open(self.session_id)
            self._last_observation = float("-inf")
            self._best_evidence_score = -1
        if self.event_id is None:
            return
        self._save_representative_evidence(frame)
        just_confirmed = self.person_confirmed and not previously_confirmed
        self._save_observation_if_due(frame, just_confirmed)
        if transition.closed:
            self._close_occurrence(interrupted=False)

    def _save_representative_evidence(self, frame: FrameAnalysis) -> None:
        score = max((person.confidence for person in frame.people_in_region), default=0)
        if score > self._best_evidence_score:
            self.store.evidence(self.event_id, frame.image, frame.annotated)
            self._best_evidence_score = score

    def _save_observation_if_due(self, frame: FrameAnalysis, just_confirmed: bool) -> None:
        elapsed = frame.processed_at - self._last_observation
        if elapsed < OBSERVATION_INTERVAL_SECONDS and not just_confirmed:
            return
        self.store.observation(
            self.event_id,
            frame.motion_score,
            len(frame.people_in_region),
            serialized(frame.detections, self.region),
        )
        self.store.update(self.event_id, self.rules.state)
        self._last_observation = frame.processed_at

    def _close_occurrence(self, *, interrupted: bool) -> None:
        if self.event_id is not None and self.rules.state is not None:
            self.store.update(self.event_id, self.rules.state, close=True, interrupted=interrupted)
        self.event_id = None
        self.rules.reset()

    def interrupt(self, *, failed: bool) -> None:
        if self.rules.state:
            self.rules.state.failed |= failed
        self._close_occurrence(interrupted=True)
