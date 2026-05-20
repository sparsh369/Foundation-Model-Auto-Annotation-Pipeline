"""Dataset export to standard annotation formats.

Each exporter consumes a normalized list of `ExportImage` records (decoupled from the DB)
and returns bytes ready to upload to object storage.
"""
from __future__ import annotations

from ml.exporters.base import ExportAnnotation, ExportImage, Exporter
from ml.exporters.coco import COCOExporter
from ml.exporters.cvat import CVATExporter
from ml.exporters.labelstudio import LabelStudioExporter
from ml.exporters.voc import PascalVOCExporter
from ml.exporters.yolo import YOLOExporter

_REGISTRY: dict[str, type[Exporter]] = {
    "coco": COCOExporter,
    "yolo": YOLOExporter,
    "pascal_voc": PascalVOCExporter,
    "cvat_xml": CVATExporter,
    "label_studio": LabelStudioExporter,
}


def get_exporter(fmt: str) -> Exporter:
    if fmt not in _REGISTRY:
        raise ValueError(f"unknown export format: {fmt}")
    return _REGISTRY[fmt]()


__all__ = ["ExportAnnotation", "ExportImage", "Exporter", "get_exporter"]
