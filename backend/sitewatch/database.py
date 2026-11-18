from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from .config import Settings
from .models import MonitoringSession, Occurrence, Source, utcnow


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = create_engine(
            settings.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 3}
        )
        self.session = sessionmaker(self.engine, expire_on_commit=False)

    def prepare(self) -> None:
        """Seed the one local source and reconcile a previous unclean shutdown."""
        with self.session.begin() as db:
            if db.scalar(select(Source).limit(1)) is None:
                db.add(
                    Source(
                        camera_index=self.settings.camera_index,
                        confidence=self.settings.confidence_threshold,
                        motion_threshold=self.settings.motion_threshold,
                    )
                )
            db.execute(
                update(MonitoringSession)
                .where(MonitoringSession.ended_at.is_(None))
                .values(
                    status="interrupted",
                    ended_at=utcnow(),
                    error="Application exited without closing the session.",
                )
            )
            # Keep positive evidence, but never turn an interrupted event into a negative.
            db.execute(
                update(Occurrence)
                .where(Occurrence.status == "active")
                .values(status="interrupted", ended_at=utcnow())
            )

    def source(self) -> Source:
        with self.session() as db:
            source = db.scalar(select(Source).order_by(Source.created_at).limit(1))
            if source is None:
                raise RuntimeError("No source configured. Run migrations and restart the server.")
            return source
