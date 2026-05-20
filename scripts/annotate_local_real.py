"""Real-model local annotation runner — FOR TESTING ONLY.

Standalone counterpart to `annotate_local.py` that runs **actual** Grounding DINO +
CLIP inference (no mocks). It deliberately does NOT import the production model wrappers
(`ml/models/*`) so the working pipeline stays untouched; it only reuses the unchanged
confidence engine, types, and exporters.

Detection : Grounding DINO  (HF `IDEA-Research/grounding-dino-tiny`, auto-downloaded)
Validation: CLIP            (open_clip `ViT-B-32`, auto-downloaded)
Routing   : ml.confidence.engine  (your real, unchanged engine)
Segmentation: skipped here (SAM 2 needs a checkpoint + the `sam2` package).

Install deps once:   pip install -r requirements-test.txt
Run:                 python -m scripts.annotate_local_real --images ./samples \
                         --prompts "car,person,dog" --out ./outputs_real --box-threshold 0.25

Notes:
  * Works on CPU (slow on first run while weights download). Set --device cuda on a GPU.
  * Synthetic/noise images will yield few or no detections — that is expected. Point it at
    real photographs to see meaningful boxes.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# Reused, UNCHANGED production components:
from ml.confidence.engine import engine as confidence_engine
from ml.exporters import ExportAnnotation, ExportImage, get_exporter
from ml.types import BBox, Detection, ImageAnnotation

_COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#46f0f0", "#f032e6"]
_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class RealDetector:
    """Grounding DINO loaded directly via transformers (version-tolerant post-process)."""

    def __init__(self, device: str) -> None:
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self.torch = torch
        self.device = device
        model_id = "IDEA-Research/grounding-dino-tiny"
        print(f"[load] grounding-dino ({model_id}) on {device} …")
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = (
            AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(device).eval()
        )

    def detect(
        self, image: np.ndarray, prompts: list[str], box_threshold: float, text_threshold: float
    ) -> list[Detection]:
        torch = self.torch
        caption = ". ".join(p.lower().strip() for p in prompts) + "."
        pil = Image.fromarray(image)
        inputs = self.processor(images=pil, text=caption, return_tensors="pt").to(self.device)
        with torch.inference_mode():
            outputs = self.model(**inputs)

        target_sizes = [pil.size[::-1]]  # (h, w)
        # transformers renamed `box_threshold` -> `threshold` across versions; try both.
        try:
            results = self.processor.post_process_grounded_object_detection(
                outputs,
                inputs.input_ids,
                threshold=box_threshold,
                text_threshold=text_threshold,
                target_sizes=target_sizes,
            )[0]
        except TypeError:
            results = self.processor.post_process_grounded_object_detection(
                outputs,
                inputs.input_ids,
                box_threshold=box_threshold,
                text_threshold=text_threshold,
                target_sizes=target_sizes,
            )[0]

        labels = results.get("text_labels", results.get("labels"))
        dets: list[Detection] = []
        for box, score, label in zip(results["boxes"], results["scores"], labels, strict=False):
            x1, y1, x2, y2 = (float(v) for v in box.tolist())
            dets.append(
                Detection(label=str(label), box=BBox(x1, y1, x2, y2), det_score=float(score))
            )
        return dets


class RealCLIP:
    """CLIP validation via open_clip (paired crop↔label cosine similarity)."""

    def __init__(self, device: str) -> None:
        import open_clip
        import torch

        self.torch = torch
        self.device = device
        print(f"[load] CLIP (ViT-B-32 / laion2b_s34b_b79k) on {device} …")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k", device=device
        )
        self.model.eval()
        self.tokenizer = open_clip.get_tokenizer("ViT-B-32")

    def validate(self, image: np.ndarray, detections: list[Detection]) -> None:
        if not detections:
            return
        torch = self.torch
        crops, labels = [], []
        for d in detections:
            x1, y1, x2, y2 = (int(max(0, v)) for v in (d.box.x1, d.box.y1, d.box.x2, d.box.y2))
            crop = image[y1:y2, x1:x2]
            crops.append(self.preprocess(Image.fromarray(crop if crop.size else image)))
            labels.append(d.label)
        with torch.inference_mode():
            img_feat = self.model.encode_image(torch.stack(crops).to(self.device))
            txt_feat = self.model.encode_text(self.tokenizer(labels).to(self.device))
            img_feat /= img_feat.norm(dim=-1, keepdim=True)
            txt_feat /= txt_feat.norm(dim=-1, keepdim=True)
            sims = (img_feat * txt_feat).sum(dim=-1)
        for d, s in zip(detections, sims.tolist(), strict=False):
            d.clip_score = float((s + 1) / 2)  # [-1,1] -> [0,1]


def _draw(src: Path, ann: ImageAnnotation, dst: Path) -> None:
    img = Image.open(src).convert("RGB")
    draw = ImageDraw.Draw(img)
    for i, d in enumerate(ann.detections):
        c = _COLORS[i % len(_COLORS)]
        draw.rectangle([d.box.x1, d.box.y1, d.box.x2, d.box.y2], outline=c, width=3)
        conf = d.confidence if d.confidence is not None else d.det_score
        draw.text((d.box.x1 + 3, max(0, d.box.y1 - 12)), f"{d.label} {conf:.2f}", fill=c)
    img.save(dst)


def main() -> None:
    ap = argparse.ArgumentParser(description="Real-model local annotation (testing)")
    ap.add_argument("--images", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", default="./outputs_real")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda", "mps"])
    ap.add_argument("--box-threshold", type=float, default=0.25)
    ap.add_argument("--text-threshold", type=float, default=0.20)
    args = ap.parse_args()

    prompts = [p.strip() for p in args.prompts.split(",") if p.strip()]
    in_dir, out_dir = Path(args.images), Path(args.out)
    (out_dir / "overlays").mkdir(parents=True, exist_ok=True)
    paths = sorted(p for p in in_dir.iterdir() if p.suffix.lower() in _EXTS)
    if not paths:
        raise SystemExit(f"No images in {in_dir}")

    detector = RealDetector(args.device)
    clip = RealCLIP(args.device)

    export_images: list[ExportImage] = []
    class_names: set[str] = set()
    print(f"\n{'image':<28}{'routing':<14}{'conf':>6}{'#det':>5}")
    print("-" * 60)
    for p in paths:
        image = np.array(Image.open(p).convert("RGB"))
        h, w = image.shape[:2]
        ann = ImageAnnotation(image_id=p.name, width=w, height=h)
        ann.detections = detector.detect(image, prompts, args.box_threshold, args.text_threshold)
        clip.validate(image, ann.detections)
        conf = confidence_engine.score_image(ann)  # reuse unchanged engine

        _draw(p, ann, out_dir / "overlays" / p.name)
        anns = []
        for d in ann.detections:
            class_names.add(d.label)
            anns.append(ExportAnnotation(label=d.label, bbox=d.box.xywh, score=round(d.det_score, 4)))
        export_images.append(ExportImage(p.name, p.name, w, h, anns))
        print(f"{p.name:<28}{conf['routing']:<14}{conf['overall']:>6.2f}{conf['n_detections']:>5}")

    coco = get_exporter("coco").export(export_images, sorted(class_names))
    (out_dir / "annotations_coco.json").write_bytes(coco)
    print(f"\nWrote overlays + annotations_coco.json to {out_dir.resolve()}")


if __name__ == "__main__":
    main()
