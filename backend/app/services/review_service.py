from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.annotation import Annotation
from backend.app.models.enums import (
    AnnotationSource,
    AnnotationStatus,
    ReviewDecision,
)
from backend.app.models.review import Review
from backend.app.schemas.annotation import ReviewSubmit


async def review_queue(
    db: AsyncSession, offset: int, limit: int
) -> tuple[list[Annotation], int]:
    from sqlalchemy import func

    cond = Annotation.status == AnnotationStatus.NEEDS_REVIEW
    total = (await db.execute(select(func.count(Annotation.id)).where(cond))).scalar_one()
    rows = (
        await db.execute(
            select(Annotation).where(cond).order_by(Annotation.created_at).offset(offset).limit(limit)
        )
    ).scalars().all()
    return list(rows), total


async def submit_review(
    db: AsyncSession,
    *,
    annotation: Annotation,
    payload: ReviewSubmit,
    reviewer_id: uuid.UUID | None,
) -> Annotation:
    """Apply a reviewer decision. Corrections create a NEW annotation version so the
    pipeline's original output is never destroyed (full lineage)."""
    db.add(
        Review(
            annotation_id=annotation.id,
            reviewer_id=reviewer_id,
            decision=payload.decision,
            corrected_payload=payload.corrected_payload,
            notes=payload.notes,
        )
    )

    if payload.decision == ReviewDecision.APPROVE:
        annotation.status = AnnotationStatus.HUMAN_APPROVED
        await db.flush()
        return annotation

    if payload.decision == ReviewDecision.REJECT:
        annotation.status = AnnotationStatus.REJECTED
        await db.flush()
        return annotation

    # CORRECT → write a new version
    corrected = payload.corrected_payload or {}
    new_version = Annotation(
        image_id=annotation.image_id,
        job_id=annotation.job_id,
        version=annotation.version + 1,
        status=AnnotationStatus.HUMAN_CORRECTED,
        source=AnnotationSource.HUMAN,
        detections=corrected.get("detections", annotation.detections),
        caption=corrected.get("caption", annotation.caption),
        tags=corrected.get("tags", annotation.tags),
        confidence={**annotation.confidence, "human_corrected": True},
    )
    db.add(new_version)
    await db.flush()
    return new_version
