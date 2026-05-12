from __future__ import annotations

import os
import pickle
import tempfile
from argparse import Namespace
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class NoteDetection:
    x1: int
    y1: int
    x2: int
    y2: int
    pitch_class: str  # one of C D E F G A B


# ── ONNX session cache (persists across pages within one process) ──────────────

_session_cache: dict[str, object] = {}


def _patch_oemer_sessions() -> None:
    """Replace oemer's per-call InferenceSession creation with cached sessions."""
    import oemer.inference as _oi
    import onnxruntime as rt

    original = _oi.inference

    def _cached(model_path, img_path, step_size=128, batch_size=16,
                 manual_th=None, use_tf=False):
        if use_tf:
            return original(model_path, img_path, step_size, batch_size,
                            manual_th, use_tf)

        onnx_path = os.path.join(model_path, "model.onnx")
        if onnx_path not in _session_cache:
            meta = pickle.load(
                open(os.path.join(model_path, "metadata.pkl"), "rb")
            )
            providers = [
                ("CUDAExecutionProvider", {"device_id": 0}),
                "CPUExecutionProvider",
            ]
            _session_cache[onnx_path] = {
                "sess": rt.InferenceSession(onnx_path, providers=providers),
                "output_names": meta["output_names"],
                "input_shape": meta["input_shape"],
                "output_shape": meta["output_shape"],
            }
            active = _session_cache[onnx_path]["sess"].get_providers()
            print(f"  Loaded {os.path.basename(onnx_path)} → {active[0]}")

        cached = _session_cache[onnx_path]
        sess = cached["sess"]
        output_names = cached["output_names"]
        input_shape = cached["input_shape"]
        output_shape = cached["output_shape"]

        from PIL import Image
        image_pil = Image.open(img_path).convert("RGB")
        image_pil = _oi.resize_image(image_pil)
        image = np.array(image_pil)

        win_size = input_shape[1]
        patches = []
        for y in range(0, image.shape[0], step_size):
            if y + win_size > image.shape[0]:
                y = image.shape[0] - win_size
            for x in range(0, image.shape[1], step_size):
                if x + win_size > image.shape[1]:
                    x = image.shape[1] - win_size
                patches.append(image[y:y + win_size, x:x + win_size])

        pred = []
        for i in range(0, len(patches), batch_size):
            batch = np.array(patches[i:i + batch_size])
            print(f"    {i + 1}/{len(patches)}", end="\r")
            out = sess.run(output_names, {"input": batch})[0]
            pred.append(out)

        out_shape = image.shape[:2] + (output_shape[-1],)
        out = np.zeros(out_shape, dtype=np.float32)
        mask = np.zeros(out_shape, dtype=np.float32)
        idx = 0
        for y in range(0, image.shape[0], step_size):
            if y + win_size > image.shape[0]:
                y = image.shape[0] - win_size
            for x in range(0, image.shape[1], step_size):
                if x + win_size > image.shape[1]:
                    x = image.shape[1] - win_size
                b, r = divmod(idx, batch_size)
                out[y:y + win_size, x:x + win_size] += pred[b][r]
                mask[y:y + win_size, x:x + win_size] += 1
                idx += 1

        out /= mask
        if manual_th is None:
            return np.argmax(out, axis=-1), out

        class_map = np.zeros(out.shape[:2] + (len(manual_th),))
        for i, th in enumerate(manual_th):
            class_map[..., i] = np.where(out[..., i + 1] > th, 1, 0)
        return class_map, out

    _oi.inference = _cached


_patch_oemer_sessions()


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_notes(img_path: str) -> list[NoteDetection]:
    """
    Run oemer's full OMR pipeline on one page image and return every notehead
    with its bounding box (in the input image's pixel coordinates) and pitch
    class letter (C–B).
    """
    from oemer import layers
    from oemer.ete import extract, clear_data
    from oemer.build_system import get_chroma_pitch
    from oemer.symbol_extraction import ClefType

    clear_data()

    with tempfile.TemporaryDirectory() as tmp:
        args = Namespace(
            img_path=img_path,
            output_path=tmp,
            use_tf=False,
            save_cache=False,
            without_deskew=False,
        )
        extract(args)

    notes = layers.get_layer("notes")
    clefs = layers.get_layer("clefs")
    oemer_img = layers.get_layer("original_image")  # resized image oemer worked on

    # Map oemer's internal pixel space → input image pixel space
    orig = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if orig is not None and oemer_img is not None:
        H_orig, W_orig = orig.shape[:2]
        H_o, W_o = oemer_img.shape[:2]
        sx, sy = W_orig / W_o, H_orig / H_o
    else:
        sx, sy = 1.0, 1.0

    # Build track → clef_type lookup
    track_clef: dict[int, ClefType] = {}
    if clefs is not None:
        for clef in clefs:
            if getattr(clef, "track", None) is not None:
                track_clef[clef.track] = clef.label

    detections: list[NoteDetection] = []
    for note in (notes if notes is not None else []):
        if note.bbox is None or note.staff_line_pos is None:
            continue
        clef_type = track_clef.get(note.track, ClefType.G_CLEF)
        pitch_class = get_chroma_pitch(note.staff_line_pos, clef_type)
        x1, y1, x2, y2 = note.bbox
        detections.append(NoteDetection(
            int(x1 * sx), int(y1 * sy),
            int(x2 * sx), int(y2 * sy),
            pitch_class,
        ))

    return detections
