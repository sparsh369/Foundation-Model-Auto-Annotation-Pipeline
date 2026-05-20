"""Stage 3 — CLIP semantic validation.

For each detection we crop the box, embed the crop and its candidate label, and compute
cosine similarity. Low similarity flags a likely DINO false-positive / label mismatch and
feeds the confidence engine's cross-model agreement term. Crops are batched.
"""
from __future__ import annotations

import hashlib

import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from ml.types import Detection

log = get_logger(__name__)


class CLIPValidator:
    version = f"clip-{settings.clip_model}"

    def __init__(self) -> None:
        self.mock = settings.pipeline_mock_models
        self._text_cache: dict[str, np.ndarray] = {}
        if self.mock:
            return
        import open_clip
        import torch

        self.device = settings.device
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            settings.clip_model, pretrained=settings.clip_pretrained, device=self.device
        )
        self.model.eval()
        self.tokenizer = open_clip.get_tokenizer(settings.clip_model)
        self._torch = torch

    def validate(self, image: np.ndarray, detections: list[Detection]) -> list[Detection]:
        if not detections:
            return detections
        if self.mock:
            return self._mock_validate(detections)

        import torch
        from PIL import Image as PILImage

        crops, labels = [], []
        for det in detections:
            x1, y1, x2, y2 = (int(max(0, v)) for v in (det.box.x1, det.box.y1, det.box.x2, det.box.y2))
            crop = image[y1:y2, x1:x2]
            if crop.size == 0:
                crop = image
            crops.append(self.preprocess(PILImage.fromarray(crop)))
            labels.append(det.label)

        img_batch = torch.stack(crops).to(self.device)
        text_tokens = self.tokenizer(labels).to(self.device)
        with torch.inference_mode(), torch.autocast(self.device, enabled=self.device == "cuda"):
            img_feat = self.model.encode_image(img_batch)
            txt_feat = self.model.encode_text(text_tokens)
            img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
            txt_feat = txt_feat / txt_feat.norm(dim=-1, keepdim=True)
            sims = (img_feat * txt_feat).sum(dim=-1)  # paired cosine sim

        for det, s in zip(detections, sims.tolist(), strict=False):
            det.clip_score = float((s + 1) / 2)  # map [-1,1] → [0,1]
        return detections

    def _mock_validate(self, detections: list[Detection]) -> list[Detection]:
        for det in detections:
            seed = int(hashlib.sha256(det.label.encode()).hexdigest(), 16) % 1000 / 1000
            det.clip_score = round(0.5 + 0.45 * (seed * det.det_score), 3)
        return detections
