"""Celery application + routing.

Queues:
  - inference        (GPU workers, prefetch=1 so a long task doesn't starve siblings)
  - export           (CPU)
  - active_learning  (CPU, low priority)
"""
from __future__ import annotations

from celery import Celery

from backend.app.core.config import settings

celery_app = Celery(
    "fm_auto_annotation",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,                  # redeliver on worker crash (idempotent tasks)
    worker_prefetch_multiplier=1,         # critical for long GPU tasks
    task_reject_on_worker_lost=True,
    result_expires=3600,
    task_default_queue="inference",
    task_routes={
        "workers.tasks.process_image": {"queue": "inference"},
        "workers.tasks.enqueue_job": {"queue": "inference"},
        "workers.tasks.export_dataset": {"queue": "export"},
        "workers.tasks.run_active_learning": {"queue": "active_learning"},
    },
    task_annotations={
        "workers.tasks.process_image": {"max_retries": 3, "default_retry_delay": 10},
    },
)
