import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from .config import ROOT, Settings, get_settings
from .database import Database
from .instance import InstanceLock
from .monitor import Monitor
from .routes.monitoring import create_monitoring_router
from .routes.occurrences import create_occurrence_router

log = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
    monitor: Monitor | None = None,
    frontend_directory: Path | None = None,
) -> FastAPI:
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
            str(request.base_url).rstrip("/"),
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

    app.include_router(create_monitoring_router(settings, database, monitor, ensure_database))
    app.include_router(create_occurrence_router(settings, database, ensure_database))

    dist = frontend_directory or ROOT / "frontend/dist"
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
