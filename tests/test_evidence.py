from uuid import uuid4

import cv2
import numpy as np
import pytest
from sitewatch.evidence import EvidenceFiles


def test_evidence_quota_fails_without_publishing_partial_images(tmp_path):
    files = EvidenceFiles(tmp_path, limit_bytes=10)
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    with pytest.raises(RuntimeError, match="quota"):
        files.save_pair(uuid4(), image, image)
    assert list(tmp_path.rglob("*.jpg")) == []


def test_evidence_keeps_original_and_annotated_files_separate(tmp_path):
    files = EvidenceFiles(tmp_path, limit_bytes=1024 * 1024)
    original = np.zeros((20, 20, 3), dtype=np.uint8)
    annotated = np.full_like(original, 255)
    event_id = uuid4()
    result = files.save_pair(event_id, original, annotated)
    assert {image.kind for image in result} == {"original", "annotated"}
    assert cv2.imread(str(tmp_path / result[0].path)).mean() == 0
    assert cv2.imread(str(tmp_path / result[1].path)).mean() == 255


def test_encoding_failure_is_explicit_and_leaves_no_published_files(tmp_path, monkeypatch):
    files = EvidenceFiles(tmp_path, limit_bytes=1024)
    monkeypatch.setattr(cv2, "imencode", lambda *args: (False, None))
    with pytest.raises(RuntimeError, match="encoding"):
        files.save_pair(uuid4(), np.zeros((10, 10, 3), dtype=np.uint8), None)
    assert list(tmp_path.rglob("*.jpg")) == []
