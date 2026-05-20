from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, get_session
from backend.app.models.annotation import Annotation
from backend.app.models.enums import AnnotationStatus
from backend.app.models.user import User
from backend.app.schemas.annotation import AnnotationOut

router = APIRouter()


@router.get("", response_model=list[AnnotationOut])
async def list_annotations(
    image_id: uuid.UUID | None = Query(None),
    status: AnnotationStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    stmt = select(Annotation).order_by(Annotation.created_at.desc()).limit(limit)
    if image_id:
        stmt = stmt.where(Annotation.image_id == image_id)
    if status:
        stmt = stmt.where(Annotation.status == status)
    return (await db.execute(stmt)).scalars().all()
