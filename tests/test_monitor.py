import time

import numpy as np
import pytest
from sitewatch.domain import Detection
from sitewatch.models import MonitoringSession, Occurrence
from sitewatch.monitor import Monitor
from sqlalchemy import select


class FakeCapture:
    def __init__(self, *args):
        self.sequence = 0
        self.error = None
        self.closed = False

    def snapshot(self):
        self.sequence += 1
        return self.sequence, time.monotonic(), np.zeros((100, 100, 3), dtype=np.uint8)

    def close(self):
        self.closed = True


class FailingDetector:
    version = "test-double"

    def __init__(self, *args):
        self.calls = 0

    def detect(self, image, confidence):
        self.calls += 1
        if self.calls > 2:
            raise RuntimeError("Controlled inference failure.")
        return [Detection(0.9, (0.1, 0.1, 0.7, 0.7))]


@pytest.mark.integration
def test_worker_failure_preserves_positive_evidence_and_closes_session(context):
    settings, database = context
    settings.inference_fps = 30
    monitor = Monitor(settings, database, FailingDetector, FakeCapture)
    monitor.start()
    monitor.thread.join(timeout=10)
    assert not monitor.running
    assert monitor.snapshot()["state"] == "error"
    assert "Controlled inference failure" in monitor.snapshot()["error"]
    with database.session() as db:
        session = db.scalar(select(MonitoringSession))
        event = db.scalar(select(Occurrence))
        assert session.status == "interrupted"
        assert event.status == "interrupted"
        assert event.classification == "person_detected"


@pytest.mark.integration
def test_camera_failure_never_creates_a_negative_occurrence(context):
    settings, database = context

    def unavailable(*args):
        raise RuntimeError("Camera unavailable.")

    monitor = Monitor(settings, database, FailingDetector, unavailable)
    monitor.start()
    monitor.thread.join(timeout=10)
    assert monitor.snapshot()["state"] == "error"
    with database.session() as db:
        assert db.scalar(select(Occurrence)) is None
        assert db.scalar(select(MonitoringSession)).status == "interrupted"
