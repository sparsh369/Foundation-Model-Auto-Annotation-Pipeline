"""Celery tasks: distributed inference fan-out, export, active learning.

Idempotency: `process_image` upserts on (image_id, version) so a redelivered task after a
worker crash never produces duplicate annotations. Job counters are updated atomically.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from celery import group
from sqlalchemy import select, update

from backend.app.core.logging import get_logger
from backend.app.models.annotation import Annotation
from backend.app.models.enums import (
    AnnotationSource,
    AnnotationStatus,
    ImageStatus,
    JobStatus,
)
from backend.app.models.image import Image
from backend.app.models.job import Job
from backend.app.services.storage import storage
from workers.celery_app import celery_app
from workers.metrics import IMAGES_FAILED, IMAGES_PROCESSED, record_gpu_mem

log = get_logger(__name__)

_ROUTING_TO_STATUS = {
    "auto_approve": AnnotationStatus.AUTO_APPROVED,
    "needs_review": AnnotationStatus.NEEDS_REVIEW,
    "reject": AnnotationStatus.REJECTED,
}


def _session():
    from backend.app.db.session import SyncSessionLocal

    return SyncSessionLocal()


@celery_app.task(name="workers.tasks.enqueue_job")
def enqueue_job(job_id: str, image_ids: list[str], params: dict) -> dict:
    """Fan a job out into one `process_image` task per image."""
    with _session() as db:
        db.execute(
            update(Job).where(Job.id == uuid.UUID(job_id)).values(status=JobStatus.RUNNING)
        )
        db.commit()

    group(process_image.s(job_id, iid, params) for iid in image_ids).apply_async()
    log.info("job_fanned_out", job_id=job_id, n=len(image_ids))
    return {"job_id": job_id, "dispatched": len(image_ids)}


@celery_app.task(
    bind=True, name="workers.tasks.process_image", acks_late=True, max_retries=3
)
def process_image(self, job_id: str, image_id: str, params: dict) -> dict:
    """Run the 5-stage pipeline for one image and persist the result."""
    from ml.pipeline import PipelineConfig, pipeline

    try:
        with _session() as db:
            image = db.get(Image, uuid.UUID(image_id))
            if image is None:
                return {"image_id": image_id, "skipped": "missing"}
            image.status = ImageStatus.PROCESSING
            db.commit()
            s3_key = image.s3_key

        image_bytes = storage.get_bytes(s3_key)
        cfg = PipelineConfig.from_params(params)
        ann, confidence = pipeline.run(image_id, image_bytes, cfg)

        detections = [
            {
                "label": d.label,
                "bbox": d.box.xywh,
                "score": round(d.det_score, 4),
                "clip_score": d.clip_score,
                "mask_quality": d.mask_quality,
                "segmentation": [d.polygon] if d.polygon else None,
                "confidence": d.confidence,
            }
            for d in ann.detections
        ]
        status = _ROUTING_TO_STATUS[confidence["routing"]]

        with _session() as db:
            # next version for this image (lineage-preserving upsert)
            current_max = db.execute(
                select(Annotation.version)
                .where(Annotation.image_id == uuid.UUID(image_id))
                .order_by(Annotation.version.desc())
                .limit(1)
            ).scalar_one_or_none()
            version = (current_max or 0) + 1

            db.add(
                Annotation(
                    image_id=uuid.UUID(image_id),
                    job_id=uuid.UUID(job_id),
                    version=version,
                    status=status,
                    source=AnnotationSource.PIPELINE,
                    detections=detections,
                    caption=ann.caption,
                    tags=ann.tags,
                    confidence=confidence,
                )
            )
            db.execute(
                update(Image)
                .where(Image.id == uuid.UUID(image_id))
                .values(status=ImageStatus.ANNOTATED)
            )
            _bump_job(db, job_id, processed=1)
            db.commit()

        IMAGES_PROCESSED.labels(confidence["routing"]).inc()
        record_gpu_mem()
        return {"image_id": image_id, "routing": confidence["routing"]}

    except Exception as exc:  # noqa: BLE001
        log.error("process_image_failed", image_id=image_id, error=str(exc))
        IMAGES_FAILED.inc()
        try:
            raise self.retry(exc=exc, countdown=10)
        except self.MaxRetriesExceededError:
            with _session() as db:
                db.execute(
                    update(Image)
                    .where(Image.id == uuid.UUID(image_id))
                    .values(status=ImageStatus.FAILED)
                )
                _bump_job(db, job_id, failed=1)
                db.commit()
            return {"image_id": image_id, "failed": True}


def _bump_job(db, job_id: str, *, processed: int = 0, failed: int = 0) -> None:
    job = db.get(Job, uuid.UUID(job_id))
    if job is None:
        return
    job.processed += processed
    job.failed += failed
    if job.processed + job.failed >= job.total:
        job.status = JobStatus.COMPLETED
        job.finished_at = datetime.now(timezone.utc)


@celery_app.task(name="workers.tasks.export_dataset")
def export_dataset(job_id: str, dataset_id: str, fmt: str) -> dict:
    """Materialize a dataset's latest annotations into the requested format."""
    from ml.exporters import ExportAnnotation, ExportImage, get_exporter

    with _session() as db:
        images = db.execute(
            select(Image).where(Image.dataset_id == uuid.UUID(dataset_id))
        ).scalars().all()

        export_images: list[ExportImage] = []
        class_names: set[str] = set()
        for img in images:
            latest = db.execute(
                select(Annotation)
                .where(Annotation.image_id == img.id)
                .order_by(Annotation.version.desc())
                .limit(1)
            ).scalar_one_or_none()
            anns = []
            if latest and latest.status != AnnotationStatus.REJECTED:
                for d in latest.detections:
                    class_names.add(d["label"])
                    anns.append(
                        ExportAnnotation(
                            label=d["label"],
                            bbox=d["bbox"],
                            score=d.get("score", 0.0),
                            segmentation=d.get("segmentation"),
                        )
                    )
            export_images.append(
                ExportImage(
                    image_id=str(img.id),
                    filename=img.filename,
                    width=img.width or 0,
                    height=img.height or 0,
                    annotations=anns,
                )
            )

        exporter = get_exporter(fmt)
        payload = exporter.export(export_images, sorted(class_names))
        key = f"exports/{dataset_id}/{job_id}.{exporter.file_extension}"
        storage.put_bytes(key, payload, exporter.media_type)

        job = db.get(Job, uuid.UUID(job_id))
        if job:
            job.status = JobStatus.COMPLETED
            job.total = job.processed = len(export_images)
            job.finished_at = datetime.now(timezone.utc)
            job.params = {**job.params, "export_key": key}
        db.commit()

    log.info("export_complete", dataset_id=dataset_id, fmt=fmt, key=key)
    return {"job_id": job_id, "key": key, "images": len(export_images)}


@celery_app.task(name="workers.tasks.run_active_learning")
def run_active_learning(dataset_id: str, review_high: float = 0.85) -> dict:
    """Mine hard/uncertain samples in a dataset and flag them for review."""
    from ml.active_learning.mining import score_candidates

    with _session() as db:
        images = db.execute(
            select(Image.id).where(Image.dataset_id == uuid.UUID(dataset_id))
        ).scalars().all()
        rows = []
        for iid in images:
            latest = db.execute(
                select(Annotation)
                .where(Annotation.image_id == iid)
                .order_by(Annotation.version.desc())
                .limit(1)
            ).scalar_one_or_none()
            if latest:
                rows.append({**latest.confidence, "image_id": str(iid)})

        candidates = score_candidates(rows, review_high=review_high)
        # Promote top candidates to NEEDS_REVIEW for the human queue.
        for c in candidates:
            db.execute(
                update(Annotation)
                .where(Annotation.image_id == uuid.UUID(c.image_id))
                .values(status=AnnotationStatus.NEEDS_REVIEW)
            )
        db.commit()

    log.info("active_learning_complete", dataset_id=dataset_id, flagged=len(candidates))
    return {"dataset_id": dataset_id, "flagged": len(candidates)}
