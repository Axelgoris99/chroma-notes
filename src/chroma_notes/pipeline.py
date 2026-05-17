from __future__ import annotations

import tempfile
from pathlib import Path

import fitz

from .omr import detect_notes
from .overlay import ColorMap, apply_overlays

RENDER_DPI = 150  # higher → better OMR accuracy, slower


def process_pdf(input_path: str, output_path: str, colors: ColorMap | None = None) -> None:
    doc = fitz.open(input_path)
    scale = 72.0 / RENDER_DPI  # pts per pixel

    for page_num, page in enumerate(doc):
        print(f"Page {page_num + 1}/{len(doc)} …")

        mat = fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img_path = f.name
        pix.save(img_path)

        try:
            detections = detect_notes(img_path)
            print(f"  {len(detections)} notes colored")
            if detections:
                apply_overlays(page, detections, scale, colors=colors)
        except Exception as exc:
            print(f"  Skipped — {exc}")
        finally:
            Path(img_path).unlink(missing_ok=True)

    doc.save(output_path)
    print(f"\nSaved → {output_path}")
