"""Stage 1 — Grounding DINO open-vocabulary detection.

Real path uses HuggingFace `IDEA-Research/grounding-dino` via transformers. Mock path
emits deterministic boxes so the full pipeline/queue/export flow runs on CPU-only hosts.
"""
from __future__ import annotations

import hashlib

import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from ml.types import BBox, Detection

log = get_logger(__name__)


class GroundingDINODetector:
    version = "grounding-dino-swint-ogc"

    def __init__(self) -> None:
        self.mock = settings.pipeline_mock_models
        if self.mock:
            return
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self.device = settings.device
        model_id = "IDEA-Research/grounding-dino-tiny"
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = (
            AutoModelForZeroShotObjectDetection.from_pretrained(model_id)
            .to(self.device)
            .eval()
        )
        self._torch = torch

    def detect(
        self,
        image: np.ndarray,
        prompts: list[str],
        box_threshold: float = 0.35,
        text_threshold: float = 0.25,
    ) -> list[Detection]:
        if self.mock:
            return self._mock_detect(image, prompts)

        import torch
        from PIL import Image as PILImage

        # Grounding DINO expects a single lowercased, '.'-separated caption.
        caption = ". ".join(p.lower().strip() for p in prompts) + "."
        pil = PILImage.fromarray(image)
        inputs = self.processor(images=pil, text=caption, return_tensors="pt").to(self.device)

        with torch.inference_mode(), torch.autocast(self.device, enabled=self.device == "cuda"):
            outputs = self.model(**inputs)

        results = self.processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            box_threshold=box_threshold,
            text_threshold=text_threshold,
            target_sizes=[pil.size[::-1]],
        )[0]

        dets: list[Detection] = []
        for box, score, label in zip(
            results["boxes"], results["scores"], results["labels"], strict=False
        ):
            x1, y1, x2, y2 = (float(v) for v in box.tolist())
            dets.append(
                Detection(label=label, box=BBox(x1, y1, x2, y2), det_score=float(score))
            )
        return dets[: settings.max_detections_per_image]

    def _mock_detect(self, image: np.ndarray, prompts: list[str]) -> list[Detection]:
        """Deterministic pseudo-detections keyed off image content hash."""
        h, w = image.shape[:2]
        seed = int(hashlib.sha256(image.tobytes()[:4096]).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        n = int(rng.integers(1, min(4, len(prompts) + 1)))
        dets: list[Detection] = []
        for i in range(n):
            cx, cy = rng.uniform(0.2, 0.8, size=2)
            bw, bh = rng.uniform(0.1, 0.3, size=2)
            x1 = max(0.0, (cx - bw / 2) * w)
            y1 = max(0.0, (cy - bh / 2) * h)
            x2 = min(float(w), (cx + bw / 2) * w)
            y2 = min(float(h), (cy + bh / 2) * h)
            dets.append(
                Detection(
                    label=prompts[i % len(prompts)],
                    box=BBox(x1, y1, x2, y2),
                    det_score=float(rng.uniform(0.4, 0.97)),
                )
            )
        return dets
