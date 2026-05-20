from __future__ import annotations

import modal

app = modal.App("chroma-notes")


def _download_checkpoints() -> None:
    import os
    from oemer.ete import CHECKPOINTS_URL, MODULE_PATH, download_file

    for title, url in CHECKPOINTS_URL.items():
        save_dir = "unet_big" if title.startswith("1st") else "seg_net"
        dst = os.path.join(MODULE_PATH, "checkpoints", save_dir)
        os.makedirs(dst, exist_ok=True)
        save_path = os.path.join(dst, title.split("_")[1])
        if not os.path.exists(save_path):
            download_file(title, url, save_path)


image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04",
        add_python="3.11",
    )
    .apt_install("libgl1", "libglib2.0-0", "libgomp1")
    .pip_install(
        "oemer",
        "onnxruntime-gpu",
        "opencv-python-headless>=4.8",
    )
    .run_function(_download_checkpoints)
    .add_local_python_source("chroma_notes")
)


@app.function(
    gpu="T4",
    image=image,
    timeout=300,
)
def detect_notes_remote(img_bytes: bytes) -> list[dict]:
    import pathlib
    import tempfile

    from chroma_notes.omr import detect_notes

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(img_bytes)
        img_path = f.name
    try:
        detections = detect_notes(img_path)
        return [
            {"x1": d.x1, "y1": d.y1, "x2": d.x2, "y2": d.y2, "pitch_class": d.pitch_class}
            for d in detections
        ]
    finally:
        pathlib.Path(img_path).unlink(missing_ok=True)
