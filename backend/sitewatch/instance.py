from pathlib import Path


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
