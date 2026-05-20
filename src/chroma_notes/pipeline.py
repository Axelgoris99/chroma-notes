from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import fitz

from .omr import NoteDetection, detect_notes
from .overlay import ColorMap, apply_overlays


_modal_fn = None


def _detect_notes(img_path: str) -> list[NoteDetection]:
    if os.environ.get("USE_MODAL"):
        try:
            global _modal_fn
            if _modal_fn is None:
                import modal
                _modal_fn = modal.Function.from_name("chroma-notes", "detect_notes_remote")
            raw = _modal_fn.remote(Path(img_path).read_bytes())
            return [NoteDetection(**d) for d in raw]
        except Exception as exc:
            print(f"  Modal failed ({exc}), falling back to local CPU")
    return detect_notes(img_path)

RENDER_DPI = 120  # higher → better OMR accuracy, slower


def process_pdf(input_path: str, output_path: str, colors: ColorMap | None = None) -> None:
    doc = fitz.open(input_path)
    scale = 72.0 / RENDER_DPI  # pts per pixel
    job_start = time.perf_counter()

    for page_num, page in enumerate(doc):
        page_start = time.perf_counter()
        print(f"Page {page_num + 1}/{len(doc)} …")

        t0 = time.perf_counter()
        mat = fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img_path = f.name
        pix.save(img_path)
        t_render = time.perf_counter() - t0

        try:
            t0 = time.perf_counter()
            detections = _detect_notes(img_path)
            t_omr = time.perf_counter() - t0

            t0 = time.perf_counter()
            if detections:
                apply_overlays(page, detections, scale, colors=colors)
            t_overlay = time.perf_counter() - t0

            t_page = time.perf_counter() - page_start
            print(
                f"  {len(detections)} notes | "
                f"render {t_render:.1f}s  omr {t_omr:.1f}s  overlay {t_overlay:.2f}s  "
                f"total {t_page:.1f}s"
            )
        except Exception as exc:
            print(f"  Skipped — {exc}")
        finally:
            Path(img_path).unlink(missing_ok=True)

    t_save = time.perf_counter()
    doc.save(output_path)
    t_save = time.perf_counter() - t_save
    t_total = time.perf_counter() - job_start
    print(f"\nSaved → {output_path}  (save {t_save:.1f}s  total {t_total:.1f}s)")
