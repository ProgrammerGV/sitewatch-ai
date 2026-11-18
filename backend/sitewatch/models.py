from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), default="Notebook webcam")
    kind: Mapped[str] = mapped_column(String(20), default="webcam")
    camera_index: Mapped[int] = mapped_column(default=0)
    roi: Mapped[list] = mapped_column(JSONB, default=lambda: [0, 0, 1, 1])
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    motion_threshold: Mapped[float] = mapped_column(Float, default=0.01)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MonitoringSession(Base):
    __tablename__ = "sessions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    model_version: Mapped[str] = mapped_column(String(160))
    configuration: Mapped[dict] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)


class Occurrence(Base):
    __tablename__ = "occurrences"
    __table_args__ = (Index("ix_occurrences_started_class", "started_at", "classification"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("sessions.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="active")
    classification: Mapped[str] = mapped_column(String(30), default="inconclusive", index=True)
    peak_people: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict] = mapped_column(JSONB, default=dict)


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (Index("ix_observations_event_time", "occurrence_id", "captured_at"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    occurrence_id: Mapped[UUID] = mapped_column(ForeignKey("occurrences.id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    analysis_status: Mapped[str] = mapped_column(String(20), default="ok")
    motion_score: Mapped[float] = mapped_column(Float)
    person_count: Mapped[int] = mapped_column(Integer)
    detections: Mapped[list] = mapped_column(JSONB)


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    occurrence_id: Mapped[UUID] = mapped_column(ForeignKey("occurrences.id"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    path: Mapped[str] = mapped_column(String(300), unique=True)
    kind: Mapped[str] = mapped_column(String(20))


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    occurrence_id: Mapped[UUID] = mapped_column(ForeignKey("occurrences.id"), index=True)
    decision: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
