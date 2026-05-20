"""Typed dataclasses passed between pipeline stages.

Keeping these framework-agnostic (plain dataclasses + numpy) lets every stage be unit
tested and mocked without importing torch.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class BBox:
    """Axis-aligned box in absolute pixel coords (xyxy)."""

    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def xywh(self) -> list[float]:
        return [self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1]

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)

    def iou(self, other: "BBox") -> float:
        ix1, iy1 = max(self.x1, other.x1), max(self.y1, other.y1)
        ix2, iy2 = min(self.x2, other.x2), min(self.y2, other.y2)
        inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        union = self.area + other.area - inter
        return inter / union if union > 0 else 0.0


@dataclass
class Detection:
    label: str
    box: BBox
    det_score: float                       # Grounding DINO confidence
    clip_score: float | None = None        # CLIP crop↔label cosine similarity
    mask: np.ndarray | None = None         # bool HxW mask from SAM 2
    mask_quality: float | None = None      # SAM 2 predicted IoU / stability
    polygon: list[list[float]] | None = None
    confidence: float | None = None        # final fused score (confidence engine)


@dataclass
class ImageAnnotation:
    image_id: str
    width: int
    height: int
    detections: list[Detection] = field(default_factory=list)
    caption: str | None = None
    tags: list[str] = field(default_factory=list)
    model_versions: dict = field(default_factory=dict)
