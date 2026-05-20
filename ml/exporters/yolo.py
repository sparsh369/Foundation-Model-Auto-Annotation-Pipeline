from __future__ import annotations

import io
import zipfile

from ml.exporters.base import ExportImage, Exporter


class YOLOExporter(Exporter):
    """YOLO TXT-per-image, zipped, with classes.txt and data.yaml."""

    file_extension = "zip"
    media_type = "application/zip"

    def export(self, images: list[ExportImage], class_names: list[str]) -> bytes:
        cats = self._class_index(class_names)
        ordered = [name for name, _ in sorted(cats.items(), key=lambda kv: kv[1])]

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("classes.txt", "\n".join(ordered))
            zf.writestr(
                "data.yaml",
                f"nc: {len(ordered)}\nnames: {ordered}\ntrain: images\nval: images\n",
            )
            for img in images:
                lines = []
                for ann in img.annotations:
                    x, y, w, h = ann.bbox
                    cx = (x + w / 2) / img.width
                    cy = (y + h / 2) / img.height
                    nw, nh = w / img.width, h / img.height
                    lines.append(f"{cats[ann.label]} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
                stem = img.filename.rsplit(".", 1)[0]
                zf.writestr(f"labels/{stem}.txt", "\n".join(lines))
        return buf.getvalue()
