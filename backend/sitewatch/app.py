import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from .config import ROOT, Settings, get_settings
from .database import Database
from .models import Evidence, Observation, Occurrence, Review
from .monitor import Monitor
from .schemas import ReviewInput, SourceUpdate

log = logging.getLogger(__name__)


def row_dict(row) -> dict:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


class InstanceLock:
    """Prevent two server processes from sharing a webcam and reconciling each other."""

    def __init__(self, path: Path):
        self.path, self.handle = path, None

    def acquire(self):
        import os

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        if self.path.stat().st_size == 0:
            self.handle.write(b"0")
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.handle.close()
            self.handle = None
            raise RuntimeError(
                "SiteWatch is already running. Use a single server process."
            ) from exc

    def release(self):
        if self.handle:
            self.handle.close()
            self.handle = None


def create_app(settings: Settings | None = None, database=None, monitor=None) -> FastAPI:
    settings = settings or get_settings()
    database = database or Database(settings)
    monitor = monitor or Monitor(settings, database)
    instance = InstanceLock(settings.absolute(settings.data_dir) / "server.lock")
    prepared = False

    def ensure_database():
        nonlocal prepared
        try:
            if not prepared:
                with monitor.control:
                    if not prepared:
                        database.prepare()
                        prepared = True
        except SQLAlchemyError:
            raise HTTPException(
                503, "PostgreSQL is unavailable or migrations are missing. See setup instructions."
            ) from None

    @asynccontextmanager
    async def lifespan(app):
        instance.acquire()
        try:
            # A missing database must not prevent diagnostics or the setup screen.
            try:
                ensure_database()
            except HTTPException:
                log.warning("Database unavailable; setup screen will remain available")
            yield
        finally:
            monitor.stop()
            database.engine.dispose()
            instance.release()

    app = FastAPI(title="SiteWatch AI", version="0.1.0", lifespan=lifespan)
    app.state.monitor, app.state.database = monitor, database
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        permitted = {
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        }
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin not in permitted:
            return JSONResponse(
                {"detail": "Only the local application can change monitoring state."},
                status_code=403,
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = (
            "no-store" if request.url.path.startswith("/api") else "no-cache"
        )
        return response

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        log.error("Database request failed: %s", type(exc).__name__)
        return JSONResponse(
            {"detail": "Database operation failed. Check PostgreSQL and migrations."},
            status_code=503,
        )

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        try:
            ensure_database()
            with database.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            db_ok = True
        except (HTTPException, SQLAlchemyError):
            db_ok = False
        model_ok = settings.absolute(settings.model_path).is_file()
        return JSONResponse(
            {
                "database": db_ok,
                "model_available": model_ok,
                "monitor": monitor.snapshot()["state"],
            },
            status_code=200 if db_ok and model_ok else 503,
        )

    @app.get("/api/source")
    def source():
        ensure_database()
        return row_dict(database.source())

    @app.patch("/api/source")
    def update_source(body: SourceUpdate):
        ensure_database()
        with monitor.control:
            if monitor.running:
                raise HTTPException(409, "Stop monitoring before changing the source or region.")
            row = database.source()
            with database.session.begin() as db:
                for key, value in body.model_dump().items():
                    setattr(row, key, list(value) if key == "roi" else value)
                db.merge(row)
            return row_dict(row)

    @app.get("/api/monitor/status")
    def status():
        return monitor.snapshot()

    @app.post("/api/monitor/start")
    def start():
        ensure_database()
        if not settings.absolute(settings.model_path).is_file():
            raise HTTPException(409, "Model missing. Run: sitewatch download-model")
        return monitor.start()

    @app.post("/api/monitor/stop")
    def stop():
        return monitor.stop()

    @app.get("/api/monitor/stream")
    async def stream(request: Request):
        async def frames():
            while not await request.is_disconnected():
                frame = monitor.frame()
                if frame:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                await asyncio.sleep(0.15)

        return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/occurrences")
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

    @app.get("/api/occurrences/{event_id}")
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

    @app.post("/api/occurrences/{event_id}/reviews", status_code=201)
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

    @app.get("/api/evidence/{evidence_id}")
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

    dist = ROOT / "frontend/dist"
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        if (dist / "index.html").is_file():
            return FileResponse(dist / "index.html")
        return JSONResponse(
            {
                "application": "SiteWatch AI",
                "next_step": "Build the frontend or run Vite on port 5173.",
                "docs": "/docs",
            }
        )

    return app
