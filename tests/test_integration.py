import numpy as np
import pytest
from fastapi.testclient import TestClient
from sitewatch.app import InstanceLock, create_app
from sitewatch.domain import EventState
from sitewatch.models import MonitoringSession, Occurrence, Review
from sitewatch.storage import EventStore
from sqlalchemy import select


@pytest.mark.integration
def test_evidence_review_and_classification_remain_separate(context):
    settings, database = context
    app = create_app(settings, database)
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        store = EventStore(database, settings.data_dir, 10)
        session = store.session_start(database.source(), "test-model", {})
        event = store.event_open(session)
        state = EventState(0, 1, person_confirmed=True)
        state.sample(1, 2, True)
        store.update(event, state, close=True)
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        store.evidence(event, image, image)
        result = client.get(f"/api/occurrences/{event}").json()
        assert result["classification"] == "person_detected"
        assert len(result["evidence"]) == 2
        evidence = client.get(f"/api/evidence/{result['evidence'][0]['id']}")
        assert evidence.status_code == 200
        assert evidence.headers["content-type"] == "image/jpeg"
        review = client.post(
            f"/api/occurrences/{event}/reviews", json={"decision": "uncertain", "note": "Occluded"}
        )
        assert review.status_code == 201
        result = client.get(f"/api/occurrences/{event}").json()
        assert result["classification"] == "person_detected"
        assert result["reviews"][0]["decision"] == "uncertain"
        assert client.get("/api/occurrences?classification=person_detected").json()["total"] == 1
        assert client.get("/api/occurrences?classification=no_person_detected").json()["total"] == 0
        with database.session() as db:
            assert len(db.scalars(select(Review)).all()) == 1


@pytest.mark.integration
def test_restart_reconciles_open_sessions_without_negative_classification(context):
    settings, database = context
    store = EventStore(database, settings.data_dir, 10)
    session = store.session_start(database.source(), "test", {})
    event = store.event_open(session)
    database.prepare()
    with database.session() as db:
        assert db.get(MonitoringSession, session).status == "interrupted"
        assert db.get(Occurrence, event).status == "interrupted"
        assert db.get(Occurrence, event).classification == "inconclusive"


@pytest.mark.integration
def test_api_validation_missing_model_and_cross_origin_protection(context):
    settings, database = context
    with TestClient(create_app(settings, database), base_url="http://127.0.0.1:8000") as client:
        assert client.post("/api/monitor/start").status_code == 409
        assert (
            client.post(
                "/api/monitor/start", headers={"Origin": "https://untrusted.example"}
            ).status_code
            == 403
        )
        assert client.get("/api/occurrences?page=0").status_code == 422
        source = client.get("/api/source").json()
        source["roi"] = [0.9, 0.9, 0.5, 0.5]
        assert client.patch("/api/source", json=source).status_code == 422
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 503


def test_single_instance_guard_releases_after_shutdown(tmp_path):
    first, second = InstanceLock(tmp_path / "test.lock"), InstanceLock(tmp_path / "test.lock")
    first.acquire()
    try:
        with pytest.raises(RuntimeError):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()
