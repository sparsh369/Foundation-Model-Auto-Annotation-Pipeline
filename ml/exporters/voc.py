from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile

from ml.exporters.base import ExportImage, Exporter


def _sub(parent: ET.Element, tag: str, text: str) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


class PascalVOCExporter(Exporter):
    """One XML per image (Pascal VOC), zipped."""

    file_extension = "zip"
    media_type = "application/zip"

    def export(self, images: list[ExportImage], class_names: list[str]) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for img in images:
                ann_el = ET.Element("annotation")
                _sub(ann_el, "filename", img.filename)
                size = ET.SubElement(ann_el, "size")
                _sub(size, "width", str(img.width))
                _sub(size, "height", str(img.height))
                _sub(size, "depth", "3")
                for a in img.annotations:
                    x, y, w, h = a.bbox
                    obj = ET.SubElement(ann_el, "object")
                    _sub(obj, "name", a.label)
                    _sub(obj, "difficult", "0")
                    bnd = ET.SubElement(obj, "bndbox")
                    _sub(bnd, "xmin", str(int(x)))
                    _sub(bnd, "ymin", str(int(y)))
                    _sub(bnd, "xmax", str(int(x + w)))
                    _sub(bnd, "ymax", str(int(y + h)))
                stem = img.filename.rsplit(".", 1)[0]
                zf.writestr(f"{stem}.xml", ET.tostring(ann_el, encoding="unicode"))
        return buf.getvalue()
