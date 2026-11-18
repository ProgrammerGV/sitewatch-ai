import cv2
import numpy as np
from sitewatch.domain import Detection
from sitewatch.vision import MotionDetector, annotate


def test_blank_static_scene_is_quiet_after_adaptation():
    detector = MotionDetector(0)
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    for _ in range(8):
        score, warmed = detector.score(image, [0, 0, 1, 1])
    assert warmed and score == 0
    moving = image.copy()
    cv2.rectangle(moving, (50, 50), (150, 150), (255, 255, 255), -1)
    score, _ = detector.score(moving, [0, 0, 1, 1])
    assert score > 0.01


def test_preview_does_not_change_original_evidence():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    annotated = annotate(image, [Detection(0.9, (0.1, 0.1, 0.8, 0.8))], [0, 0, 1, 1])
    assert not image.any()
    assert annotated.any()
