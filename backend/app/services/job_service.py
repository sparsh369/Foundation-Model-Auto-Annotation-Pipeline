from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger
from backend.app.models.enums import ImageStatus, JobStatus, JobType
from backend.app.models.image import Image
from backend.app.models.job import Job

log = get_logger(__name__)


async def create_job(
    db: AsyncSession,
    *,
    dataset_id: uuid.UUID,
    job_type: JobType,
    params: dict,
    created_by: uuid.UUID | None,
) -> Job:
    pending = (
        await db.execute(
            select(Image.id).where(
                Image.dataset_id == dataset_id, Image.status == ImageStatus.PENDING
            )
        )
    ).scalars().all()

    job = Job(
        dataset_id=dataset_id,
        type=job_type,
        status=JobStatus.QUEUED,
        total=len(pending),
        params=params,
        created_by=created_by,
    )
    db.add(job)
    await db.flush()
    return job, list(pending)


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    return await db.get(Job, job_id)


def dispatch_inference(job_id: uuid.UUID, image_ids: list[uuid.UUID], params: dict) -> None:
    """Hand the job off to the Celery fan-out. Imported lazily to avoid a hard
    dependency on the broker when the API is imported in tooling/tests."""
    from workers.tasks import enqueue_job

    enqueue_job.delay(str(job_id), [str(i) for i in image_ids], params)
    log.info("dispatched inference job", job_id=str(job_id), images=len(image_ids))
