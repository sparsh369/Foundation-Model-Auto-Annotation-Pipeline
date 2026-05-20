from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.models.enums import AnnotationSource, AnnotationStatus, ReviewDecision
from backend.app.schemas.common import ORMModel


class Detection(BaseModel):
    label: str
    bbox: list[float] = Field(min_length=4, max_length=4, description="[x, y, w, h] in px")
    score: float = Field(ge=0, le=1)
    segmentation: list[list[float]] | None = None  # polygon(s) or RLE-as-list
    clip_score: float | None = None
    mask_quality: float | None = None


class AnnotationOut(ORMModel):
    id: uuid.UUID
    image_id: uuid.UUID
    job_id: uuid.UUID | None
    version: int
    status: AnnotationStatus
    source: AnnotationSource
    detections: list[dict]
    caption: str | None
    tags: list[str]
    confidence: dict
    created_at: datetime


class ReviewSubmit(BaseModel):
    decision: ReviewDecision
    corrected_payload: dict | None = None  # {detections, caption, tags}
    notes: str | None = None


class ReviewOut(ORMModel):
    id: uuid.UUID
    annotation_id: uuid.UUID
    reviewer_id: uuid.UUID | None
    decision: ReviewDecision
    notes: str | None
    created_at: datetime
