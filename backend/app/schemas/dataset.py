from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.models.enums import DatasetStatus
from backend.app.schemas.common import ORMModel


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class DatasetOut(ORMModel):
    id: uuid.UUID
    name: str
    description: str | None
    owner_id: uuid.UUID | None
    image_count: int
    status: DatasetStatus
    created_at: datetime


class PresignRequest(BaseModel):
    filenames: list[str] = Field(min_length=1, max_length=1000)


class PresignedUpload(BaseModel):
    filename: str
    s3_key: str
    upload_url: str


class PresignResponse(BaseModel):
    uploads: list[PresignedUpload]


class RegisterImage(BaseModel):
    filename: str
    s3_key: str
    width: int | None = None
    height: int | None = None
    sha256: str | None = None


class RegisterImagesRequest(BaseModel):
    images: list[RegisterImage] = Field(min_length=1, max_length=1000)
