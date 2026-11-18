import hashlib
import time
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from .domain import Detection


class YoloDetector:
    """Model loaded once; no network downloads inside the monitoring request."""

    def __init__(self, model_path: Path, device: str):
        if not model_path.is_file():
            raise RuntimeError("Model missing. Run: sitewatch download-model")
        import os

        os.environ.setdefault("YOLO_CONFIG_DIR", str(model_path.parent.parent / "ultralytics"))
        from ultralytics import YOLO, settings

        settings.update({"sync": False})
        self.model = YOLO(str(model_path))
        self.device = device
        self.version = (
            f"{model_path.name}:sha256:{hashlib.sha256(model_path.read_bytes()).hexdigest()}"
        )

    def detect(self, image: np.ndarray, confidence: float) -> list[Detection]:
        result = self.model.predict(image, conf=confidence, device=self.device, verbose=False)[0]
        return [
            Detection(float(box.conf.item()), tuple(box.xyxyn[0].tolist()))
            for box in result.boxes
            if result.names[int(box.cls.item())] == "person"
        ]


class MotionDetector:
    def __init__(self, warmup_seconds: float):
        self.background = cv2.createBackgroundSubtractorMOG2(
            history=150, varThreshold=25, detectShadows=True
        )
        self.started = time.monotonic()
        self.warmup = warmup_seconds

    def score(self, image: np.ndarray, roi: list[float]) -> tuple[float, bool]:
        h, w = image.shape[:2]
        x, y, rw, rh = roi
        crop = image[
            int(y * h) : max(int((y + rh) * h), int(y * h) + 1),
            int(x * w) : max(int((x + rw) * w), int(x * w) + 1),
        ]
        mask = self.background.apply(crop)
        # Ignore shadow pixels (127); only strong foreground (255) is motion.
        mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)[1]
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        score = float(np.count_nonzero(mask)) / mask.size
        return score, time.monotonic() - self.started >= self.warmup


def annotate(image: np.ndarray, detections: list[Detection], roi: list[float]) -> np.ndarray:
    view = image.copy()
    h, w = view.shape[:2]
    x, y, rw, rh = roi
    cv2.rectangle(
        view,
        (int(x * w), int(y * h)),
        (int((x + rw) * w) - 1, int((y + rh) * h) - 1),
        (230, 190, 70),
        2,
    )
    for detection in detections:
        a, b, c, d = detection.bbox
        color = (120, 230, 80) if detection.in_region(tuple(roi)) else (150, 150, 150)
        cv2.rectangle(view, (int(a * w), int(b * h)), (int(c * w), int(d * h)), color, 2)
        cv2.putText(
            view,
            f"Person {detection.confidence:.2f}",
            (int(a * w), max(18, int(b * h) - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )
    return view


def serialized(detections: list[Detection], roi: list[float]) -> list[dict]:
    return [{**asdict(d), "in_region": d.in_region(tuple(roi))} for d in detections]
