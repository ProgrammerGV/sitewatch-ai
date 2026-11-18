import argparse
import logging
import os
import time
from pathlib import Path

from .config import ROOT, get_settings


def main():
    parser = argparse.ArgumentParser(description="SiteWatch AI local video analytics")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="Serve the API and built frontend at 127.0.0.1:8000")
    commands.add_parser("migrate", help="Apply database migrations")
    commands.add_parser("download-model", help="Download the official pretrained YOLO model")
    replay = commands.add_parser(
        "replay", help="Analyze a local video with the real model and event pipeline"
    )
    replay.add_argument("file", type=Path)
    replay.add_argument("--seconds", type=float, default=30)
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = get_settings()
    if args.command == "serve":
        import uvicorn

        from .app import create_app

        uvicorn.run(create_app(settings), host="127.0.0.1", port=8000, workers=1)
    elif args.command == "migrate":
        from alembic import command
        from alembic.config import Config

        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "backend/migrations"))
        command.upgrade(config, "head")
    elif args.command == "download-model":
        os.environ.setdefault(
            "YOLO_CONFIG_DIR", str(settings.absolute(settings.data_dir) / "ultralytics")
        )
        from ultralytics import YOLO

        target = settings.absolute(settings.model_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        previous = Path.cwd()
        try:
            os.chdir(target.parent)
            YOLO(settings.model_name)
            downloaded = target.parent / settings.model_name
            if downloaded != target:
                import shutil

                shutil.copyfile(downloaded, target)
            if not target.is_file():
                raise RuntimeError("Model download did not create the expected file.")
            print(f"Model ready: {target}")
        finally:
            os.chdir(previous)
    elif args.command == "replay":
        if not args.file.is_file():
            parser.error("Video file does not exist.")
        from .app import InstanceLock
        from .database import Database
        from .monitor import Monitor

        instance = InstanceLock(settings.absolute(settings.data_dir) / "server.lock")
        instance.acquire()
        db = Database(settings)
        monitor = Monitor(settings, db)
        try:
            db.prepare()
            monitor.start(args.file.resolve())
            deadline = time.monotonic() + args.seconds
            while monitor.running and time.monotonic() < deadline:
                time.sleep(0.5)
            monitor.stop()
            import json

            print(json.dumps(monitor.snapshot(), indent=2))
            if monitor.snapshot()["error"]:
                raise SystemExit(1)
        finally:
            monitor.stop()
            db.engine.dispose()
            instance.release()


if __name__ == "__main__":
    main()
