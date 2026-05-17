from __future__ import annotations

import fitz

from .colors import BOOMWHACKER
from .omr import NoteDetection

FILL_OPACITY = 0.40

ColorMap = dict[str, tuple[float, float, float]]


def apply_overlays(
    page: fitz.Page,
    detections: list[NoteDetection],
    scale: float,
    colors: ColorMap | None = None,
) -> None:
    palette = colors if colors is not None else BOOMWHACKER
    shape = page.new_shape()

    for det in detections:
        color = palette.get(det.pitch_class)
        if color is None:
            continue

        cx = ((det.x1 + det.x2) / 2) * scale
        cy = ((det.y1 + det.y2) / 2) * scale
        # Slightly oversize the circle so it frames the notehead visually
        r = max(det.x2 - det.x1, det.y2 - det.y1) / 2 * scale * 1.25

        shape.draw_circle(fitz.Point(cx, cy), r)
        shape.finish(fill=color, fill_opacity=FILL_OPACITY, color=None, width=0)

    shape.commit()
