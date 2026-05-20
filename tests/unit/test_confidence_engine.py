from __future__ import annotations

import numpy as np

from ml.confidence.engine import ConfidenceEngine, Routing, Weights
from ml.types import BBox, Detection, ImageAnnotation


def _det(label: str, det: float, clip: float, mq: float, box: BBox, mask: BBox) -> Detection:
    d = Detection(label=label, box=box, det_score=det, clip_score=clip, mask_quality=mq)
    m = np.zeros((100, 100), dtype=bool)
    m[int(mask.y1) : int(mask.y2), int(mask.x1) : int(mask.x2)] = True
    d.mask = m
    return d


def test_weights_normalize_to_one():
    w = Weights().normalized()
    total = w.detection + w.clip + w.mask_quality + w.box_consistency + w.agreement
    assert abs(total - 1.0) < 1e-6


def test_high_agreement_auto_approves():
    box = BBox(10, 10, 60, 60)
    ann = ImageAnnotation(image_id="x", width=100, height=100)
    ann.detections = [_det("cat", 0.95, 0.95, 0.95, box, box)]
    out = ConfidenceEngine().score_image(ann)
    assert out["routing"] == Routing.AUTO_APPROVE.value
    assert out["overall"] >= 0.85


def test_disagreement_routes_to_review():
    box = BBox(10, 10, 60, 60)
    far = BBox(70, 70, 95, 95)  # mask far from box → low consistency
    ann = ImageAnnotation(image_id="x", width=100, height=100)
    ann.detections = [_det("cat", 0.9, 0.2, 0.4, box, far)]
    out = ConfidenceEngine().score_image(ann)
    assert out["routing"] in (Routing.NEEDS_REVIEW.value, Routing.REJECT.value)


def test_empty_detections_needs_review():
    ann = ImageAnnotation(image_id="x", width=100, height=100)
    out = ConfidenceEngine().score_image(ann)
    assert out["routing"] == Routing.NEEDS_REVIEW.value
    assert out["n_detections"] == 0
