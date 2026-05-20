from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin, UUIDMixin
from backend.app.models.enums import DatasetStatus


class Dataset(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    image_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[DatasetStatus] = mapped_column(
        String(32), default=DatasetStatus.CREATED, nullable=False
    )

    images = relationship("Image", back_populates="dataset", cascade="all, delete-orphan")
