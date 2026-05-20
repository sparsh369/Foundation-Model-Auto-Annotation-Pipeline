from __future__ import annotations

import json

from ml.exporters.base import ExportImage, Exporter


class COCOExporter(Exporter):
    """COCO detection+segmentation JSON (single file)."""

    file_extension = "json"

    def export(self, images: list[ExportImage], class_names: list[str]) -> bytes:
        cats = self._class_index(class_names)
        categories = [{"id": idx + 1, "name": name} for name, idx in cats.items()]

        coco_images, annotations = [], []
        ann_id = 1
        for img_idx, img in enumerate(images, start=1):
            coco_images.append(
                {
                    "id": img_idx,
                    "file_name": img.filename,
                    "width": img.width,
                    "height": img.height,
                }
            )
            for ann in img.annotations:
                x, y, w, h = ann.bbox
                entry = {
                    "id": ann_id,
                    "image_id": img_idx,
                    "category_id": cats[ann.label] + 1,
                    "bbox": [x, y, w, h],
                    "area": w * h,
                    "iscrowd": 0,
                    "score": ann.score,
                }
                if ann.segmentation:
                    entry["segmentation"] = [
                        [c for point in poly for c in point] if poly and isinstance(poly[0], list)
                        else poly
                        for poly in ann.segmentation
                    ]
                annotations.append(entry)
                ann_id += 1

        doc = {
            "info": {"description": "FM Auto-Annotation export", "version": "1.0"},
            "images": coco_images,
            "annotations": annotations,
            "categories": categories,
        }
        return json.dumps(doc, indent=2).encode()
