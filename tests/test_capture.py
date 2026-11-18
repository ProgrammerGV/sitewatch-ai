import cv2
import numpy as np
from sitewatch.capture import LatestFrameCapture


def test_recorded_video_completion_is_distinct_from_capture_failure(tmp_path):
    video = tmp_path / "finite.avi"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 30, (64, 64))
    assert writer.isOpened()
    for _ in range(2):
        writer.write(np.zeros((64, 64, 3), dtype=np.uint8))
    writer.release()
    capture = LatestFrameCapture(0, video)
    try:
        capture.thread.join(timeout=3)
        assert capture.finished
        assert capture.error is None
        assert capture.snapshot().sequence == 2
    finally:
        capture.close()
