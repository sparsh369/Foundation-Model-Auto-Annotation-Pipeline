from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass
class ExportAnnotation:
    label: str
    bbox: list[float]  # [x, y, w, h] absolute px
    score: float
    segmentation: list[list[float]] | None = None  # list of polygons (flattened xy)


@dataclass
class ExportImage:
    image_id: str
    filename: str
    width: int
    height: int
    annotations: list[ExportAnnotation] = field(default_factory=list)


class Exporter(abc.ABC):
    """Serialize a dataset's images+annotations into a single archive's bytes."""

    file_extension: str = "json"
    media_type: str = "application/json"

    @abc.abstractmethod
    def export(self, images: list[ExportImage], class_names: list[str]) -> bytes: ...

    @staticmethod
    def _class_index(class_names: list[str]) -> dict[str, int]:
        return {name: i for i, name in enumerate(sorted(set(class_names)))}
