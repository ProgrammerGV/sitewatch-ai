"""JPEG encoding and bounded filesystem storage, without database dependencies."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

import cv2
import numpy as np

from .policy import JPEG_QUALITY


@dataclass(frozen=True)
class StoredImage:
    kind: Literal["original", "annotated"]
    path: str


class EvidenceFiles:
    def __init__(self, root: Path, limit_bytes: int):
        self.root, self.limit_bytes = root, limit_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def save_pair(
        self, event_id: UUID, original: np.ndarray, annotated: np.ndarray
    ) -> list[StoredImage]:
        images = [("original", self._encode(original)), ("annotated", self._encode(annotated))]
        self._check_quota(sum(len(content) for _, content in images))
        folder = self.root / str(event_id)
        folder.mkdir(exist_ok=True)
        stored = []
        for kind, content in images:
            temporary = folder / f"{kind}.tmp"
            temporary.write_bytes(content)
            os.replace(temporary, folder / f"{kind}.jpg")
            stored.append(StoredImage(kind=kind, path=f"{event_id}/{kind}.jpg"))
        return stored

    @staticmethod
    def _encode(image: np.ndarray) -> bytes:
        ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        if not ok:
            raise RuntimeError("Evidence JPEG encoding failed.")
        return encoded.tobytes()

    def _check_quota(self, additional_bytes: int) -> None:
        used = sum(path.stat().st_size for path in self.root.rglob("*.jpg"))
        if used + additional_bytes > self.limit_bytes:
            raise RuntimeError(
                "Evidence storage quota reached. Archive or remove local evidence before restarting."
            )
