from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.dataset import Dataset
from backend.app.models.enums import DatasetStatus
from backend.app.models.image import Image
from backend.app.schemas.dataset import DatasetCreate, RegisterImage
from backend.app.services.storage import storage


async def create_dataset(db: AsyncSession, payload: DatasetCreate, owner_id: uuid.UUID) -> Dataset:
    ds = Dataset(name=payload.name, description=payload.description, owner_id=owner_id)
    db.add(ds)
    await db.flush()
    return ds


async def get_dataset(db: AsyncSession, dataset_id: uuid.UUID) -> Dataset | None:
    return await db.get(Dataset, dataset_id)


async def list_datasets(db: AsyncSession, offset: int, limit: int) -> tuple[list[Dataset], int]:
    total = (await db.execute(select(func.count(Dataset.id)))).scalar_one()
    rows = (
        await db.execute(
            select(Dataset).order_by(Dataset.created_at.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()
    return list(rows), total


def presign_uploads(dataset_id: uuid.UUID, filenames: list[str]) -> list[dict]:
    out = []
    for fn in filenames:
        key = storage.build_key(dataset_id, fn)
        out.append({"filename": fn, "s3_key": key, "upload_url": storage.presign_put(key)})
    return out


async def register_images(
    db: AsyncSession, dataset: Dataset, images: list[RegisterImage]
) -> int:
    db.add_all(
        [
            Image(
                dataset_id=dataset.id,
                s3_key=img.s3_key,
                filename=img.filename,
                width=img.width,
                height=img.height,
                sha256=img.sha256,
            )
            for img in images
        ]
    )
    dataset.image_count += len(images)
    dataset.status = DatasetStatus.READY
    await db.flush()
    return len(images)
