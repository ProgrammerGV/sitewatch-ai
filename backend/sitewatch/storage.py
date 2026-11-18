from datetime import timedelta
from pathlib import Path
from uuid import UUID

import numpy as np
from sqlalchemy import select

from .database import Database
from .domain import EventState
from .evidence import EvidenceFiles
from .models import Evidence, MonitoringSession, Observation, Occurrence, Source, utcnow
from .policy import MEBIBYTE


class EventStore:
    def __init__(self, database: Database, data_dir: Path, max_mb: int):
        self.database = database
        self.files = EvidenceFiles(data_dir / "evidence", max_mb * MEBIBYTE)

    def session_start(self, source: Source, version: str, configuration: dict) -> UUID:
        with self.database.session.begin() as db:
            row = MonitoringSession(
                source_id=source.id, model_version=version, configuration=configuration
            )
            db.add(row)
            db.flush()
            return row.id

    def event_open(self, session_id: UUID) -> UUID:
        with self.database.session.begin() as db:
            row = Occurrence(session_id=session_id)
            db.add(row)
            db.flush()
            return row.id

    def observation(
        self, event_id: UUID, score: float, people: int, detections: list[dict]
    ) -> None:
        with self.database.session.begin() as db:
            db.add(
                Observation(
                    occurrence_id=event_id,
                    motion_score=score,
                    person_count=people,
                    detections=detections,
                )
            )

    def update(
        self, event_id: UUID, state: EventState, *, close: bool = False, interrupted: bool = False
    ) -> None:
        with self.database.session.begin() as db:
            row = db.get(Occurrence, event_id)
            if row is None:
                raise RuntimeError("Active occurrence no longer exists.")
            row.classification = state.classify(interrupted)
            row.peak_people = state.peak_people
            row.summary = {
                "valid_samples": state.valid_samples,
                "max_analysis_gap_seconds": round(state.max_gap, 3),
                "analysis_failed": state.failed,
            }
            # Monotonic elapsed time is mapped back onto UTC for audit timestamps.
            row.last_activity_at = row.started_at + timedelta(
                seconds=state.last_activity - state.started
            )
            if close:
                row.ended_at = utcnow()
                row.status = "interrupted" if interrupted else "closed"

    def evidence(self, event_id: UUID, original: np.ndarray, annotated: np.ndarray) -> None:
        images = self.files.save_pair(event_id, original, annotated)
        with self.database.session.begin() as db:
            existing = {
                e.kind: e
                for e in db.scalars(select(Evidence).where(Evidence.occurrence_id == event_id))
            }
            for image in images:
                if image.kind in existing:
                    existing[image.kind].captured_at = utcnow()
                else:
                    db.add(Evidence(occurrence_id=event_id, kind=image.kind, path=image.path))

    def session_end(self, session_id: UUID, error: str | None) -> None:
        with self.database.session.begin() as db:
            row = db.get(MonitoringSession, session_id)
            if row:
                row.status = "interrupted" if error else "closed"
                row.ended_at = utcnow()
                row.error = error
