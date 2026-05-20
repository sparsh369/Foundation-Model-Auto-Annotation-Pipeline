from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin, UUIDMixin
from backend.app.models.enums import AnnotationSource, AnnotationStatus


class Annotation(UUIDMixin, TimestampMixin, Base):
    """One versioned annotation record for an image.

    A new `version` is written on each re-annotation or human correction so the full
    lineage is preserved (never destructive). The latest version is the active one.
    """

    __tablename__ = "annotations"
    __table_args__ = (
        UniqueConstraint("image_id", "version", name="uq_annotation_image_version"),
    )

    image_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[AnnotationStatus] = mapped_column(String(32), nullable=False)
    source: Mapped[AnnotationSource] = mapped_column(
        String(16), default=AnnotationSource.PIPELINE, nullable=False
    )

    # Per-detection payloads: list[{label, bbox:[x,y,w,h], score, segmentation, ...}]
    detections: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Confidence breakdown: {overall, detection, clip, agreement, mask_quality, ...}
    confidence: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    image = relationship("Image", back_populates="annotations")
    reviews = relationship(
        "Review", back_populates="annotation", cascade="all, delete-orphan"
    )
