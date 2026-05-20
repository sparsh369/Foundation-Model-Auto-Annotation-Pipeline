from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_session, require_permission
from backend.app.core.rbac import Permission
from backend.app.models.annotation import Annotation
from backend.app.models.user import User
from backend.app.schemas.annotation import AnnotationOut, ReviewSubmit
from backend.app.schemas.common import Page
from backend.app.services import review_service
from backend.app.services.audit import record

router = APIRouter()


@router.get("/queue", response_model=Page[AnnotationOut])
async def queue(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.REVIEW_SUBMIT)),
):
    rows, total = await review_service.review_queue(db, (page - 1) * size, size)
    return Page(items=rows, total=total, page=page, size=size)


@router.post("/{annotation_id}", response_model=AnnotationOut)
async def submit(
    annotation_id: uuid.UUID,
    payload: ReviewSubmit,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.REVIEW_SUBMIT)),
):
    annotation = await db.get(Annotation, annotation_id)
    if not annotation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "annotation not found")
    result = await review_service.submit_review(
        db, annotation=annotation, payload=payload, reviewer_id=user.id
    )
    await record(
        db,
        actor_id=user.id,
        action=f"review.{payload.decision.value}",
        entity_type="annotation",
        entity_id=str(annotation_id),
    )
    return result
