from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, get_session, require_permission
from backend.app.core.rbac import Permission
from backend.app.models.enums import JobStatus, JobType
from backend.app.models.user import User
from backend.app.schemas.job import ExportCreate, JobCreate, JobOut
from backend.app.services import dataset_service, job_service
from backend.app.services.audit import record

router = APIRouter()


@router.post("", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.JOB_CREATE)),
):
    if not await dataset_service.get_dataset(db, payload.dataset_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dataset not found")

    job, image_ids = await job_service.create_job(
        db,
        dataset_id=payload.dataset_id,
        job_type=payload.type,
        params=payload.params,
        created_by=user.id,
    )
    await db.flush()
    await record(db, actor_id=user.id, action="job.create", entity_type="job", entity_id=str(job.id))
    # commit happens in get_db; dispatch after we know the job row is persisted
    await db.commit()
    job_service.dispatch_inference(job.id, image_ids, payload.params)
    return job


@router.post("/exports", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    payload: ExportCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.EXPORT_CREATE)),
):
    if not await dataset_service.get_dataset(db, payload.dataset_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dataset not found")
    job, _ = await job_service.create_job(
        db,
        dataset_id=payload.dataset_id,
        job_type=JobType.EXPORT,
        params={"format": payload.format.value},
        created_by=user.id,
    )
    await db.commit()
    from workers.tasks import export_dataset

    export_dataset.delay(str(job.id), str(payload.dataset_id), payload.format.value)
    return job


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    job = await job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    return job


@router.post("/{job_id}:cancel", response_model=JobOut)
async def cancel_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.JOB_CANCEL)),
):
    job = await job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
        raise HTTPException(status.HTTP_409_CONFLICT, "job already finished")
    job.status = JobStatus.CANCELLED
    await record(db, actor_id=user.id, action="job.cancel", entity_type="job", entity_id=str(job.id))
    return job
