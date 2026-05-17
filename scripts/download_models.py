"""Download oemer ONNX checkpoints into the package directory."""
import os
from oemer.ete import CHECKPOINTS_URL, MODULE_PATH, download_file

chk = os.path.join(MODULE_PATH, "checkpoints/unet_big/model.onnx")
if os.path.exists(chk):
    print("Checkpoints already present, skipping download.")
else:
    for title, url in CHECKPOINTS_URL.items():
        save_dir = "unet_big" if title.startswith("1st") else "seg_net"
        dst = os.path.join(MODULE_PATH, "checkpoints", save_dir)
        os.makedirs(dst, exist_ok=True)
        save_path = os.path.join(dst, title.split("_")[1])
        download_file(title, url, save_path)
    print("Done.")
