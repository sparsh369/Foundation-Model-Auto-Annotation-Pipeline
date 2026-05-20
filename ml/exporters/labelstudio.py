from __future__ import annotations

import json

from ml.exporters.base import ExportImage, Exporter


class LabelStudioExporter(Exporter):
    """Label Studio JSON import format (predictions with bbox results)."""

    file_extension = "json"

    def export(self, images: list[ExportImage], class_names: list[str]) -> bytes:
        tasks = []
        for img in images:
            results = []
            for a in img.annotations:
                x, y, w, h = a.bbox
                results.append(
                    {
                        "type": "rectanglelabels",
                        "from_name": "label",
                        "to_name": "image",
                        "original_width": img.width,
                        "original_height": img.height,
                        "value": {
                            "x": 100 * x / img.width,
                            "y": 100 * y / img.height,
                            "width": 100 * w / img.width,
                            "height": 100 * h / img.height,
                            "rotation": 0,
                            "rectanglelabels": [a.label],
                        },
                    }
                )
            tasks.append(
                {
                    "data": {"image": img.filename},
                    "predictions": [{"model_version": "fm-auto-annotation", "result": results}],
                }
            )
        return json.dumps(tasks, indent=2).encode()
