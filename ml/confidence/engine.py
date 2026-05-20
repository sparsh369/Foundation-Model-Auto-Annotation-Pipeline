"""Confidence scoring & routing engine.

Fuses heterogeneous signals into a single per-detection confidence and an image-level
routing decision (auto-approve / human-review / reject). The weights are configurable and
the design is intentionally transparent (linear ensemble) so the score is auditable and
explainable to reviewers — black-box calibrators can be swapped in behind `score_detection`.

Signals
-------
- detection confidence  (Grounding DINO)         — does an object exist here?
- CLIP cosine similarity (crop ↔ label)          — is the label semantically right?
- mask quality          (SAM 2 predicted IoU)    — is the mask trustworthy?
- box consistency       (box vs mask bbox IoU)   — do detection & segmentation agree?
- cross-model agreement (DINO ∧ CLIP ∧ mask)     — multi-signal corroboration
- uncertainty           (entropy of signals)     — penalize disagreement
"""
from __future__ import annotations

import enum
import math
from dataclasses import dataclass

import numpy as np

from backend.app.core.config import settings
from ml.types import Detection, ImageAnnotation


class Routing(str, enum.Enum):
    AUTO_APPROVE = "auto_approve"
    NEEDS_REVIEW = "needs_review"
    REJECT = "reject"


@dataclass
class Weights:
    detection: float = 0.30
    clip: float = 0.25
    mask_quality: float = 0.20
    box_consistency: float = 0.15
    agreement: float = 0.10

    def normalized(self) -> "Weights":
        total = self.detection + self.clip + self.mask_quality + self.box_consistency + self.agreement
        if total == 0:
            return self
        return Weights(
            self.detection / total,
            self.clip / total,
            self.mask_quality / total,
            self.box_consistency / total,
            self.agreement / total,
        )


def _mask_bbox_iou(det: Detection) -> float:
    """IoU between the detection box and the tight bbox of its mask."""
    if det.mask is None or not det.mask.any():
        return 0.0
    ys, xs = np.where(det.mask)
    from ml.types import BBox

    mask_box = BBox(float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))
    return det.box.iou(mask_box)


def _entropy_penalty(signals: list[float]) -> float:
    """Higher when signals disagree (spread out); 0 when they all agree.
    Returns a multiplicative factor in (0, 1]."""
    arr = np.clip(np.array(signals, dtype=float), 1e-6, 1.0)
    var = float(np.var(arr))
    return math.exp(-3.0 * var)  # variance 0 → 1.0; high variance → ~0


class ConfidenceEngine:
    def __init__(self, weights: Weights | None = None) -> None:
        self.w = (weights or Weights()).normalized()
        self.auto = settings.conf_auto_approve
        self.review = settings.conf_human_review
        self.reject = settings.conf_reject

    def score_detection(self, det: Detection) -> float:
        clip = det.clip_score if det.clip_score is not None else 0.5
        mq = det.mask_quality if det.mask_quality is not None else 0.5
        consistency = _mask_bbox_iou(det)
        agreement = float(np.mean([det.det_score, clip, mq, consistency]))

        base = (
            self.w.detection * det.det_score
            + self.w.clip * clip
            + self.w.mask_quality * mq
            + self.w.box_consistency * consistency
            + self.w.agreement * agreement
        )
        score = base * _entropy_penalty([det.det_score, clip, mq, consistency])
        det.confidence = round(float(np.clip(score, 0.0, 1.0)), 4)
        return det.confidence

    def score_image(self, ann: ImageAnnotation) -> dict:
        """Score every detection and produce an image-level routing decision."""
        if not ann.detections:
            return {"overall": 0.0, "routing": Routing.NEEDS_REVIEW.value, "n_detections": 0}

        per = [self.score_detection(d) for d in ann.detections]
        overall = float(np.mean(per))
        # An image is only as trustworthy as its weakest accepted detection.
        weakest = float(np.min(per))

        if overall >= self.auto and weakest >= self.review:
            routing = Routing.AUTO_APPROVE
        elif overall < self.reject:
            routing = Routing.REJECT
        else:
            routing = Routing.NEEDS_REVIEW

        return {
            "overall": round(overall, 4),
            "weakest": round(weakest, 4),
            "mean_detection": round(float(np.mean([d.det_score for d in ann.detections])), 4),
            "mean_clip": round(
                float(np.mean([d.clip_score or 0.0 for d in ann.detections])), 4
            ),
            "mean_mask_quality": round(
                float(np.mean([d.mask_quality or 0.0 for d in ann.detections])), 4
            ),
            "routing": routing.value,
            "n_detections": len(ann.detections),
        }


engine = ConfidenceEngine()
