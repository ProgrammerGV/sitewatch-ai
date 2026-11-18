import os
from pathlib import Path
from uuid import UUID

import cv2
import numpy as np
from sqlalchemy import select

from .database import Database
from .domain import EventState
from .models import Evidence, MonitoringSession, Observation, Occurrence, Source, utcnow


class EventStore:
    def __init__(self, database: Database, data_dir: Path, max_mb: int):
        self.database = database
        self.root = data_dir / "evidence"
        self.limit = max_mb * 1024 * 1024
        self.root.mkdir(parents=True, exist_ok=True)

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
            from datetime import timedelta

            row.last_activity_at = row.started_at + timedelta(
                seconds=state.last_activity - state.started
            )
            if close:
                row.ended_at = utcnow()
                row.status = "interrupted" if interrupted else "closed"

    def evidence(self, event_id: UUID, original: np.ndarray, annotated: np.ndarray) -> None:
        folder = self.root / str(event_id)
        folder.mkdir(exist_ok=True)
        used = sum(p.stat().st_size for p in self.root.rglob("*.jpg"))
        images = []
        for kind, image in (("original", original), ("annotated", annotated)):
            ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 88])
            if not ok:
                raise RuntimeError("Evidence JPEG encoding failed.")
            images.append((kind, encoded.tobytes()))
        if used + sum(len(content) for _, content in images) > self.limit:
            raise RuntimeError(
                "Evidence storage quota reached. Archive or remove local evidence before restarting."
            )
        for kind, content in images:
            target = folder / f"{kind}.jpg"
            temp = folder / f"{kind}.tmp"
            temp.write_bytes(content)
            os.replace(temp, target)
        with self.database.session.begin() as db:
            existing = {
                e.kind: e
                for e in db.scalars(select(Evidence).where(Evidence.occurrence_id == event_id))
            }
            for kind, _ in images:
                if kind in existing:
                    existing[kind].captured_at = utcnow()
                else:
                    db.add(
                        Evidence(occurrence_id=event_id, kind=kind, path=f"{event_id}/{kind}.jpg")
                    )

    def session_end(self, session_id: UUID, error: str | None) -> None:
        with self.database.session.begin() as db:
            row = db.get(MonitoringSession, session_id)
            if row:
                row.status = "interrupted" if error else "closed"
                row.ended_at = utcnow()
                row.error = error
