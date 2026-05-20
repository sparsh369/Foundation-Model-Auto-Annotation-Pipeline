from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin, UUIDMixin
from backend.app.models.enums import ImageStatus


class Image(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "images"
    __table_args__ = (Index("ix_images_dataset_status", "dataset_id", "status"),)

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[ImageStatus] = mapped_column(
        String(32), default=ImageStatus.PENDING, nullable=False
    )

    dataset = relationship("Dataset", back_populates="images")
    annotations = relationship(
        "Annotation", back_populates="image", cascade="all, delete-orphan"
    )
