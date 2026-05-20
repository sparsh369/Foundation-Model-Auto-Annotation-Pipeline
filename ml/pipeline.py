"""Five-stage auto-annotation orchestrator.

    image bytes ─▶ [1] Grounding DINO ─▶ [2] SAM 2 ─▶ [3] CLIP ─▶ [4] VLM ─▶ [5] confidence

Each stage is independently mockable. The orchestrator returns a fully-scored
`ImageAnnotation` plus the routing decision; persistence is the worker's job.
"""
from __future__ import annotations

import io
import time
from dataclasses import dataclass

import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from ml.confidence.engine import engine as confidence_engine
from ml.registry import registry
from ml.types import ImageAnnotation

log = get_logger(__name__)


@dataclass
class PipelineConfig:
    prompts: list[str]
    box_threshold: float = 0.35
    text_threshold: float = 0.25
    enable_segmentation: bool = True
    enable_vlm: bool = True
    # Only call the (expensive) VLM when image-level confidence is ambiguous.
    vlm_ambiguity_gate: tuple[float, float] = (0.35, 0.9)

    @classmethod
    def from_params(cls, params: dict) -> "PipelineConfig":
        return cls(
            prompts=params.get("prompts") or ["object"],
            box_threshold=params.get("box_threshold", 0.35),
            text_threshold=params.get("text_threshold", 0.25),
            enable_segmentation=params.get("enable_segmentation", True),
            enable_vlm=params.get("enable_vlm", True),
        )


def _decode_image(data: bytes) -> np.ndarray:
    from PIL import Image as PILImage

    return np.array(PILImage.open(io.BytesIO(data)).convert("RGB"))


class AutoAnnotationPipeline:
    def run(self, image_id: str, image_bytes: bytes, cfg: PipelineConfig) -> tuple[ImageAnnotation, dict]:
        t0 = time.perf_counter()
        image = _decode_image(image_bytes)
        h, w = image.shape[:2]
        ann = ImageAnnotation(image_id=image_id, width=w, height=h)
        timings: dict[str, float] = {}

        # ── Stage 1: detection ──────────────────────────────────
        ts = time.perf_counter()
        ann.detections = registry.detector.detect(
            image, cfg.prompts, cfg.box_threshold, cfg.text_threshold
        )
        timings["detect"] = round(time.perf_counter() - ts, 4)
        ann.model_versions["detector"] = registry.detector.version

        # ── Stage 2: segmentation ───────────────────────────────
        if cfg.enable_segmentation and ann.detections:
            ts = time.perf_counter()
            ann.detections = registry.segmenter.segment(image, ann.detections)
            timings["segment"] = round(time.perf_counter() - ts, 4)
            ann.model_versions["segmenter"] = registry.segmenter.version

        # ── Stage 3: CLIP validation ────────────────────────────
        if ann.detections:
            ts = time.perf_counter()
            ann.detections = registry.clip.validate(image, ann.detections)
            timings["clip"] = round(time.perf_counter() - ts, 4)
            ann.model_versions["clip"] = registry.clip.version

        # ── Stage 5a: preliminary confidence (drives VLM gate) ──
        prelim = confidence_engine.score_image(ann)

        # ── Stage 4: VLM captioning (gated) ─────────────────────
        lo, hi = cfg.vlm_ambiguity_gate
        should_vlm = cfg.enable_vlm and (lo <= prelim["overall"] <= hi or not ann.detections)
        if should_vlm:
            ts = time.perf_counter()
            vlm_out = registry.vlm.caption(image, [d.label for d in ann.detections])
            ann.caption = vlm_out.get("caption")
            ann.tags = vlm_out.get("tags", [])
            timings["vlm"] = round(time.perf_counter() - ts, 4)
            ann.model_versions["vlm"] = registry.vlm.version

        # ── Stage 5b: final confidence + routing ────────────────
        confidence = confidence_engine.score_image(ann)
        confidence["timings"] = timings
        confidence["total_seconds"] = round(time.perf_counter() - t0, 4)
        confidence["vlm_invoked"] = should_vlm

        log.info(
            "pipeline_complete",
            image_id=image_id,
            routing=confidence["routing"],
            overall=confidence["overall"],
            n=confidence["n_detections"],
            seconds=confidence["total_seconds"],
        )
        return ann, confidence


pipeline = AutoAnnotationPipeline()
