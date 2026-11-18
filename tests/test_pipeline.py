from uuid import uuid4

import numpy as np
import pytest
from sitewatch.domain import Detection, EventRules
from sitewatch.pipeline import FrameAnalysis, FrameAnalyzer, FrameSettings, OccurrenceRecorder


class MemoryPersistence:
    def __init__(self):
        self.opened = []
        self.samples = []
        self.images = []
        self.updates = []

    def event_open(self, session_id):
        event_id = uuid4()
        self.opened.append((session_id, event_id))
        return event_id

    def evidence(self, event_id, original, annotated):
        self.images.append(event_id)

    def observation(self, event_id, score, people, detections):
        self.samples.append((event_id, people))

    def update(self, event_id, state, *, close=False, interrupted=False):
        self.updates.append((event_id, state.classify(interrupted), close, interrupted))


def frame(now, *, people=0, motion=False):
    image = np.zeros((40, 40, 3), dtype=np.uint8)
    detections = [Detection(0.9, (0.1, 0.1, 0.8, 0.8)) for _ in range(people)]
    return FrameAnalysis(
        image, image, detections, detections, 0.1 if motion else 0, motion, True, now, now, 0
    )


def test_human_confirmation_is_persisted_between_regular_observation_intervals():
    persistence = MemoryPersistence()
    recorder = OccurrenceRecorder(persistence, EventRules(), uuid4(), [0, 0, 1, 1])
    recorder.record(frame(0, motion=True))
    recorder.record(frame(0.5, motion=True))
    recorder.record(frame(0.7, people=1))
    recorder.record(frame(1, people=1))
    assert len(persistence.opened) == 1
    assert [people for _, people in persistence.samples] == [0, 1]
    assert recorder.person_confirmed


def test_interrupt_never_turns_motion_only_evidence_into_a_negative():
    persistence = MemoryPersistence()
    recorder = OccurrenceRecorder(persistence, EventRules(), uuid4(), [0, 0, 1, 1])
    for now in (0, 0.5, 1, 1.5):
        recorder.record(frame(now, motion=True))
    recorder.interrupt(failed=True)
    assert persistence.updates[-1][1:] == ("inconclusive", True, True)
    assert recorder.event_id is None


class CountingDetector:
    version = "test"

    def __init__(self):
        self.calls = 0

    def detect(self, image, confidence):
        self.calls += 1
        return []


def test_stale_frame_is_rejected_before_inference():
    detector = CountingDetector()
    analyzer = FrameAnalyzer(detector, FrameSettings((0, 0, 1, 1), 0.5, 0.01, 0), clock=lambda: 10)
    with pytest.raises(RuntimeError, match="stale"):
        analyzer.analyze(np.zeros((40, 40, 3), dtype=np.uint8), captured_at=7)
    assert detector.calls == 0


def test_slow_analysis_is_rejected_without_waiting_in_real_time():
    times = iter([10, 13])
    detector = CountingDetector()
    analyzer = FrameAnalyzer(
        detector, FrameSettings((0, 0, 1, 1), 0.5, 0.01, 0), clock=lambda: next(times)
    )
    with pytest.raises(RuntimeError, match="took too long"):
        analyzer.analyze(np.zeros((40, 40, 3), dtype=np.uint8), captured_at=10)
    assert detector.calls == 1
