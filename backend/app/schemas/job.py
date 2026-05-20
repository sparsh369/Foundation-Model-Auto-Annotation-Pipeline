from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.models.enums import ExportFormat, JobStatus, JobType
from backend.app.schemas.common import ORMModel


class AnnotateParams(BaseModel):
    """Open-vocabulary prompts + gates for an auto-annotation job."""

    prompts: list[str] = Field(min_length=1, description="Text classes to detect.")
    box_threshold: float = Field(default=0.35, ge=0, le=1)
    text_threshold: float = Field(default=0.25, ge=0, le=1)
    enable_vlm: bool = True
    enable_segmentation: bool = True


class JobCreate(BaseModel):
    dataset_id: uuid.UUID
    type: JobType = JobType.AUTO_ANNOTATE
    params: dict = Field(default_factory=dict)


class ExportCreate(BaseModel):
    dataset_id: uuid.UUID
    format: ExportFormat


class JobOut(ORMModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    type: JobType
    status: JobStatus
    total: int
    processed: int
    failed: int
    params: dict
    created_at: datetime
    finished_at: datetime | None

    @property
    def progress(self) -> float:
        return 0.0 if self.total == 0 else round((self.processed + self.failed) / self.total, 4)
