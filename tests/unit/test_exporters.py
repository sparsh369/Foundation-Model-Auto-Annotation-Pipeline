from __future__ import annotations

import json

from ml.exporters import get_exporter
from ml.exporters.base import ExportAnnotation, ExportImage


def _sample() -> list[ExportImage]:
    return [
        ExportImage(
            image_id="1",
            filename="a.jpg",
            width=200,
            height=100,
            annotations=[
                ExportAnnotation(label="cat", bbox=[10, 20, 30, 40], score=0.9),
                ExportAnnotation(label="dog", bbox=[50, 10, 20, 20], score=0.8),
            ],
        )
    ]


def test_coco_export_shape():
    payload = get_exporter("coco").export(_sample(), ["cat", "dog"])
    doc = json.loads(payload)
    assert len(doc["images"]) == 1
    assert len(doc["annotations"]) == 2
    assert {c["name"] for c in doc["categories"]} == {"cat", "dog"}


def test_yolo_normalization():
    import io
    import zipfile

    payload = get_exporter("yolo").export(_sample(), ["cat", "dog"])
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        txt = zf.read("labels/a.txt").decode().splitlines()
    # cat bbox [10,20,30,40] in 200x100 → cx=(10+15)/200=0.125, cy=(20+20)/100=0.4
    cls, cx, cy, w, h = txt[0].split()
    assert cls == "0"
    assert abs(float(cx) - 0.125) < 1e-6
    assert abs(float(cy) - 0.4) < 1e-6


def test_labelstudio_and_voc_and_cvat_smoke():
    for fmt in ("label_studio", "pascal_voc", "cvat_xml"):
        payload = get_exporter(fmt).export(_sample(), ["cat", "dog"])
        assert payload and len(payload) > 0
