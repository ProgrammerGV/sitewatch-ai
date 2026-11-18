from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from ..config import Settings
from ..database import Database
from ..models import Evidence, Observation, Occurrence, Review
from ..schemas import ReviewInput
from ..serialization import row_dict


def create_occurrence_router(
    settings: Settings, database: Database, ensure_database: Callable[[], None]
) -> APIRouter:
    router = APIRouter(tags=["occurrences"])

    @router.get("/api/occurrences")
    def occurrences(classification: str | None = None, page: int = 1):
        ensure_database()
        if page < 1 or classification not in {
            None,
            "person_detected",
            "no_person_detected",
            "inconclusive",
        }:
            raise HTTPException(422, "Invalid page or classification.")
        query = select(Occurrence)
        if classification:
            query = query.where(Occurrence.classification == classification)
        with database.session() as db:
            total = db.scalar(select(func.count()).select_from(query.subquery()))
            rows = db.scalars(
                query.order_by(Occurrence.started_at.desc()).offset((page - 1) * 20).limit(20)
            ).all()
            items = []
            for row in rows:
                evidence = db.scalar(
                    select(Evidence).where(
                        Evidence.occurrence_id == row.id, Evidence.kind == "annotated"
                    )
                )
                review = db.scalar(
                    select(Review)
                    .where(Review.occurrence_id == row.id)
                    .order_by(Review.created_at.desc())
                    .limit(1)
                )
                items.append(
                    {
                        **row_dict(row),
                        "evidence_id": evidence.id if evidence else None,
                        "review": row_dict(review) if review else None,
                    }
                )
            return {"items": items, "total": total, "page": page, "page_size": 20}

    @router.get("/api/occurrences/{event_id}")
    def occurrence(event_id: UUID):
        ensure_database()
        with database.session() as db:
            row = db.get(Occurrence, event_id)
            if row is None:
                raise HTTPException(404, "Occurrence not found.")
            evidence = db.scalars(select(Evidence).where(Evidence.occurrence_id == event_id)).all()
            observations = db.scalars(
                select(Observation)
                .where(Observation.occurrence_id == event_id)
                .order_by(Observation.captured_at.desc())
                .limit(100)
            ).all()
            reviews = db.scalars(
                select(Review)
                .where(Review.occurrence_id == event_id)
                .order_by(Review.created_at.desc())
            ).all()
            return {
                **row_dict(row),
                "evidence": [row_dict(e) for e in evidence],
                "observations": [row_dict(o) for o in observations],
                "reviews": [row_dict(r) for r in reviews],
            }

    @router.post("/api/occurrences/{event_id}/reviews", status_code=201)
    def review(event_id: UUID, body: ReviewInput):
        ensure_database()
        with database.session.begin() as db:
            row = db.get(Occurrence, event_id)
            if row is None:
                raise HTTPException(404, "Occurrence not found.")
            if row.status == "active":
                raise HTTPException(409, "Review the occurrence after it closes.")
            result = Review(occurrence_id=event_id, **body.model_dump())
            db.add(result)
            db.flush()
            return row_dict(result)

    @router.get("/api/evidence/{evidence_id}")
    def evidence(evidence_id: UUID):
        ensure_database()
        with database.session() as db:
            row = db.get(Evidence, evidence_id)
            if row is None:
                raise HTTPException(404, "Evidence not found.")
            root = (settings.absolute(settings.data_dir) / "evidence").resolve()
            path = (root / row.path).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise HTTPException(404, "Evidence file is unavailable.")
            return FileResponse(path, media_type="image/jpeg")

    return router
