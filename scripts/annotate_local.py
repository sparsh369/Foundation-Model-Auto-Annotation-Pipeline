"""Run the auto-annotation pipeline directly on local image files.

No database / broker / object-store required — this exercises the full 5-stage ML
pipeline + confidence engine and writes visual overlays plus a COCO export.

Usage:
    # mock mode (CPU, deterministic stub detections — no weights needed)
    PIPELINE_MOCK_MODELS=true python -m scripts.annotate_local \
        --images ./samples --prompts "car,person,dog" --out ./outputs

    # real models (needs CUDA + weights; see ml/README.md)
    PIPELINE_MOCK_MODELS=false DEVICE=cuda python -m scripts.annotate_local \
        --images ./samples --prompts "car,person,dog" --out ./outputs
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from ml.exporters import ExportAnnotation, ExportImage, get_exporter
from ml.pipeline import PipelineConfig, pipeline

_COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#46f0f0", "#f032e6"]
_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _draw_overlay(src: Path, ann, dst: Path) -> None:
    img = Image.open(src).convert("RGB")
    draw = ImageDraw.Draw(img)
    for i, det in enumerate(ann.detections):
        color = _COLORS[i % len(_COLORS)]
        x1, y1, x2, y2 = det.box.x1, det.box.y1, det.box.x2, det.box.y2
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        conf = det.confidence if det.confidence is not None else det.det_score
        draw.text((x1 + 3, max(0, y1 - 12)), f"{det.label} {conf:.2f}", fill=color)
    img.save(dst)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local auto-annotation runner")
    parser.add_argument("--images", required=True, help="Directory of images")
    parser.add_argument("--prompts", required=True, help="Comma-separated open-vocab classes")
    parser.add_argument("--out", default="./outputs", help="Output directory")
    parser.add_argument("--box-threshold", type=float, default=0.35)
    parser.add_argument("--no-vlm", action="store_true", help="Skip VLM captioning stage")
    parser.add_argument("--no-seg", action="store_true", help="Skip SAM2 segmentation stage")
    args = parser.parse_args()

    prompts = [p.strip() for p in args.prompts.split(",") if p.strip()]
    cfg = PipelineConfig(
        prompts=prompts,
        box_threshold=args.box_threshold,
        enable_vlm=not args.no_vlm,
        enable_segmentation=not args.no_seg,
    )

    in_dir = Path(args.images)
    out_dir = Path(args.out)
    (out_dir / "overlays").mkdir(parents=True, exist_ok=True)

    paths = sorted(p for p in in_dir.iterdir() if p.suffix.lower() in _EXTS)
    if not paths:
        raise SystemExit(f"No images found in {in_dir} (looked for {sorted(_EXTS)})")

    export_images: list[ExportImage] = []
    class_names: set[str] = set()

    print(f"\n{'image':<28} {'routing':<14} {'conf':>6} {'#det':>5}  caption")
    print("-" * 90)
    for p in paths:
        ann, conf = pipeline.run(p.name, p.read_bytes(), cfg)
        _draw_overlay(p, ann, out_dir / "overlays" / p.name)

        anns = []
        for d in ann.detections:
            class_names.add(d.label)
            anns.append(
                ExportAnnotation(
                    label=d.label,
                    bbox=d.box.xywh,
                    score=round(d.det_score, 4),
                    segmentation=[d.polygon] if d.polygon else None,
                )
            )
        export_images.append(
            ExportImage(p.name, p.name, ann.width, ann.height, anns)
        )
        print(
            f"{p.name:<28} {conf['routing']:<14} {conf['overall']:>6.2f} "
            f"{conf['n_detections']:>5}  {(ann.caption or '')[:40]}"
        )

    coco = get_exporter("coco").export(export_images, sorted(class_names))
    (out_dir / "annotations_coco.json").write_bytes(coco)

    summary = {
        "images": len(export_images),
        "classes": sorted(class_names),
        "auto_approved": sum(
            1 for ei in export_images for _ in [0] if ei.annotations
        ),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nWrote overlays + annotations_coco.json to {out_dir.resolve()}")


if __name__ == "__main__":
    main()
