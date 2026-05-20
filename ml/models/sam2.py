"""Stage 2 — SAM 2 promptable segmentation.

Key efficiency: the heavy image encoder runs ONCE per image; all DINO boxes are then
cheap prompts against the cached embedding. This is the dominant SAM-2 batching win.
"""
from __future__ import annotations

import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from ml.types import Detection

log = get_logger(__name__)


def _mask_to_polygon(mask: np.ndarray) -> list[list[float]]:
    """Largest external contour → flat polygon [x1,y1,x2,y2,...]."""
    import cv2

    contours, _ = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return []
    biggest = max(contours, key=cv2.contourArea)
    eps = 0.005 * cv2.arcLength(biggest, True)
    approx = cv2.approxPolyDP(biggest, eps, True).reshape(-1, 2)
    return [[float(x), float(y)] for x, y in approx]


class SAM2Segmenter:
    version = "sam2-hiera-large"

    def __init__(self) -> None:
        self.mock = settings.pipeline_mock_models
        if self.mock:
            return
        import torch
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor

        self.device = settings.device
        model = build_sam2(settings.sam2_config, settings.sam2_checkpoint, device=self.device)
        self.predictor = SAM2ImagePredictor(model)
        self._torch = torch

    def segment(self, image: np.ndarray, detections: list[Detection]) -> list[Detection]:
        if not detections:
            return detections
        if self.mock:
            return self._mock_segment(image, detections)

        import torch

        # Encode the image once, then prompt with every box.
        self.predictor.set_image(image)
        boxes = np.array([[d.box.x1, d.box.y1, d.box.x2, d.box.y2] for d in detections])
        with torch.inference_mode(), torch.autocast(self.device, enabled=self.device == "cuda"):
            masks, scores, _ = self.predictor.predict(box=boxes, multimask_output=False)

        masks = np.asarray(masks).reshape(len(detections), *image.shape[:2]) > 0.5
        scores = np.asarray(scores).reshape(len(detections), -1).max(axis=1)
        for det, mask, q in zip(detections, masks, scores, strict=False):
            det.mask = mask
            det.mask_quality = float(q)
            det.polygon = _mask_to_polygon(mask)

        if self.device == "cuda":
            torch.cuda.empty_cache()
        return detections

    def _mock_segment(self, image: np.ndarray, detections: list[Detection]) -> list[Detection]:
        h, w = image.shape[:2]
        for det in detections:
            mask = np.zeros((h, w), dtype=bool)
            x1, y1, x2, y2 = (int(v) for v in (det.box.x1, det.box.y1, det.box.x2, det.box.y2))
            mask[y1:y2, x1:x2] = True
            det.mask = mask
            det.mask_quality = round(0.6 + 0.35 * det.det_score, 3)
            det.polygon = [
                [float(x1), float(y1)],
                [float(x2), float(y1)],
                [float(x2), float(y2)],
                [float(x1), float(y2)],
            ]
        return detections
