from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, get_session, require_permission
from backend.app.core.rbac import Permission, Role
from backend.app.models.user import User
from backend.app.schemas.common import Page
from backend.app.schemas.dataset import (
    DatasetCreate,
    DatasetOut,
    PresignRequest,
    PresignResponse,
    RegisterImagesRequest,
)
from backend.app.services import dataset_service
from backend.app.services.audit import record

router = APIRouter()


@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
async def create(
    payload: DatasetCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.DATASET_CREATE)),
):
    ds = await dataset_service.create_dataset(db, payload, user.id)
    await record(db, actor_id=user.id, action="dataset.create", entity_type="dataset", entity_id=str(ds.id))
    return ds


@router.get("", response_model=Page[DatasetOut])
async def list_(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    rows, total = await dataset_service.list_datasets(db, (page - 1) * size, size)
    return Page(items=rows, total=total, page=page, size=size)


@router.get("/{dataset_id}", response_model=DatasetOut)
async def get(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    ds = await dataset_service.get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dataset not found")
    return ds


@router.post("/{dataset_id}/images:presign", response_model=PresignResponse)
async def presign(
    dataset_id: uuid.UUID,
    req: PresignRequest,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.DATASET_CREATE)),
):
    if not await dataset_service.get_dataset(db, dataset_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dataset not found")
    return PresignResponse(uploads=dataset_service.presign_uploads(dataset_id, req.filenames))


@router.post("/{dataset_id}/images:register")
async def register_images(
    dataset_id: uuid.UUID,
    req: RegisterImagesRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.DATASET_CREATE)),
):
    ds = await dataset_service.get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dataset not found")
    n = await dataset_service.register_images(db, ds, req.images)
    await record(db, actor_id=user.id, action="images.register", entity_type="dataset", entity_id=str(ds.id), meta={"count": n})
    return {"registered": n, "image_count": ds.image_count}


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.DATASET_DELETE)),
):
    ds = await dataset_service.get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dataset not found")
    if ds.owner_id != user.id and user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not owner")
    await db.delete(ds)
    await record(db, actor_id=user.id, action="dataset.delete", entity_type="dataset", entity_id=str(dataset_id))
