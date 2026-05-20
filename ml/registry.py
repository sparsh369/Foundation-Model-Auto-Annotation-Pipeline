"""Lazy, process-local model singletons.

Each Celery worker process loads each foundation model exactly once and pins it to a
device. This amortizes the multi-second load cost across all tasks the worker handles
and keeps GPU memory occupied by a single resident copy (no per-task reload thrash).
"""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from backend.app.core.config import settings
from backend.app.core.logging import get_logger

if TYPE_CHECKING:
    from ml.models.clip_validator import CLIPValidator
    from ml.models.grounding_dino import GroundingDINODetector
    from ml.models.sam2 import SAM2Segmenter
    from ml.models.vlm import VLMCaptioner

log = get_logger(__name__)


class ModelRegistry:
    """Thread-safe lazy holder. Double-checked locking avoids racey double-loads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._detector: GroundingDINODetector | None = None
        self._segmenter: SAM2Segmenter | None = None
        self._clip: CLIPValidator | None = None
        self._vlm: VLMCaptioner | None = None

    @property
    def detector(self) -> "GroundingDINODetector":
        if self._detector is None:
            with self._lock:
                if self._detector is None:
                    from ml.models.grounding_dino import GroundingDINODetector

                    log.info("loading grounding_dino", device=settings.device)
                    self._detector = GroundingDINODetector()
        return self._detector

    @property
    def segmenter(self) -> "SAM2Segmenter":
        if self._segmenter is None:
            with self._lock:
                if self._segmenter is None:
                    from ml.models.sam2 import SAM2Segmenter

                    log.info("loading sam2", device=settings.device)
                    self._segmenter = SAM2Segmenter()
        return self._segmenter

    @property
    def clip(self) -> "CLIPValidator":
        if self._clip is None:
            with self._lock:
                if self._clip is None:
                    from ml.models.clip_validator import CLIPValidator

                    log.info("loading clip", model=settings.clip_model)
                    self._clip = CLIPValidator()
        return self._clip

    @property
    def vlm(self) -> "VLMCaptioner":
        if self._vlm is None:
            with self._lock:
                if self._vlm is None:
                    from ml.models.vlm import VLMCaptioner

                    log.info("loading vlm", provider=settings.vlm_provider)
                    self._vlm = VLMCaptioner()
        return self._vlm


registry = ModelRegistry()
