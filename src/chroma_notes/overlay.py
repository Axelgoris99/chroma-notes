from __future__ import annotations

import fitz

from .colors import BOOMWHACKER
from .omr import NoteDetection

FILL_OPACITY = 0.40


def apply_overlays(page: fitz.Page, detections: list[NoteDetection], scale: float) -> None:
    """
    Draw translucent Boomwhacker circles over each detected notehead.

    scale: points-per-pixel ratio (= 72 / render_dpi). Both PyMuPDF page
    coordinates and the rendered image share a top-left origin with y going
    downward, so no axis flip is needed.
    """
    shape = page.new_shape()

    for det in detections:
        color = BOOMWHACKER.get(det.pitch_class)
        if color is None:
            continue

        cx = ((det.x1 + det.x2) / 2) * scale
        cy = ((det.y1 + det.y2) / 2) * scale
        # Slightly oversize the circle so it frames the notehead visually
        r = max(det.x2 - det.x1, det.y2 - det.y1) / 2 * scale * 1.25

        shape.draw_circle(fitz.Point(cx, cy), r)
        shape.finish(fill=color, fill_opacity=FILL_OPACITY, color=None, width=0)

    shape.commit()
