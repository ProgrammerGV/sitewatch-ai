import asyncio
from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..config import Settings
from ..database import Database
from ..monitor import Monitor
from ..schemas import SourceUpdate
from ..serialization import row_dict


def create_monitoring_router(
    settings: Settings, database: Database, monitor: Monitor, ensure_database: Callable[[], None]
) -> APIRouter:
    router = APIRouter(tags=["monitoring"])

    @router.get("/api/source")
    def source():
        ensure_database()
        return row_dict(database.source())

    @router.patch("/api/source")
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

    @router.get("/api/monitor/status")
    def status():
        return monitor.snapshot()

    @router.post("/api/monitor/start")
    def start():
        ensure_database()
        if not settings.absolute(settings.model_path).is_file():
            raise HTTPException(409, "Model missing. Run: sitewatch download-model")
        return monitor.start()

    @router.post("/api/monitor/stop")
    def stop():
        return monitor.stop()

    @router.get("/api/monitor/stream")
    async def stream(request: Request):
        async def frames():
            while not await request.is_disconnected():
                frame = monitor.frame()
                if frame:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                await asyncio.sleep(0.15)

        return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")

    return router
