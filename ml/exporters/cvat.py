from __future__ import annotations

import xml.etree.ElementTree as ET

from ml.exporters.base import ExportImage, Exporter


class CVATExporter(Exporter):
    """CVAT for images 1.1 XML."""

    file_extension = "xml"
    media_type = "application/xml"

    def export(self, images: list[ExportImage], class_names: list[str]) -> bytes:
        root = ET.Element("annotations")
        ET.SubElement(root, "version").text = "1.1"
        meta = ET.SubElement(root, "meta")
        task = ET.SubElement(meta, "task")
        ET.SubElement(task, "name").text = "fm-auto-annotation"
        labels_el = ET.SubElement(task, "labels")
        for name in sorted(set(class_names)):
            lbl = ET.SubElement(labels_el, "label")
            ET.SubElement(lbl, "name").text = name

        for idx, img in enumerate(images):
            img_el = ET.SubElement(
                root,
                "image",
                id=str(idx),
                name=img.filename,
                width=str(img.width),
                height=str(img.height),
            )
            for a in img.annotations:
                x, y, w, h = a.bbox
                box = ET.SubElement(
                    img_el,
                    "box",
                    label=a.label,
                    xtl=f"{x:.2f}",
                    ytl=f"{y:.2f}",
                    xbr=f"{x + w:.2f}",
                    ybr=f"{y + h:.2f}",
                    occluded="0",
                )
                if a.segmentation:
                    for poly in a.segmentation:
                        pts = poly if isinstance(poly[0], (int, float)) else [c for p in poly for c in p]
                        points = ";".join(
                            f"{pts[i]:.2f},{pts[i+1]:.2f}" for i in range(0, len(pts) - 1, 2)
                        )
                        ET.SubElement(img_el, "polygon", label=a.label, points=points, occluded="0")
                box.set("source", "auto")
        return b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="utf-8")
