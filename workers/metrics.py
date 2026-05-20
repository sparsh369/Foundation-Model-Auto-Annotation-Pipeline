"""Prometheus metrics exposed by worker processes (scraped on a sidecar port)."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, start_http_server

IMAGES_PROCESSED = Counter(
    "pipeline_images_processed_total", "Images processed", ["routing"]
)
IMAGES_FAILED = Counter("pipeline_images_failed_total", "Images that errored")
STAGE_LATENCY = Histogram(
    "pipeline_stage_seconds", "Per-stage latency", ["stage"]
)
GPU_MEM_BYTES = Gauge("pipeline_gpu_mem_bytes", "Resident GPU memory of this worker")


def start_metrics_server(port: int = 9100) -> None:
    start_http_server(port)


def record_gpu_mem() -> None:
    try:
        import torch

        if torch.cuda.is_available():
            GPU_MEM_BYTES.set(torch.cuda.memory_allocated())
    except Exception:  # noqa: BLE001
        pass
