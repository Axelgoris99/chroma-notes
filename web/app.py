from __future__ import annotations

import json
import os
import queue
import shutil
import threading
import time
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from chroma_notes.colors import BOOMWHACKER
from chroma_notes.pipeline import process_pdf

NOTES = list("CDEFGAB")


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


def _parse_colors(raw: str | None) -> dict[str, tuple[float, float, float]] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    result = {}
    for note in NOTES:
        val = data.get(note)
        if isinstance(val, str) and val.startswith("#") and len(val) == 7:
            result[note] = _hex_to_rgb(val)
    return result if len(result) == len(NOTES) else None

JOBS_DIR = Path(os.environ.get("JOBS_DIR", Path(__file__).parent.parent / "jobs"))
JOBS_DIR.mkdir(exist_ok=True)

MAX_WORKERS = 1
MAX_FILE_MB = 50
JOB_TTL_SECONDS = 7200  # 2 hours
RATE_LIMIT_SECONDS = 300  # 5 min per IP

app = FastAPI(title="Chroma Notes")

jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()

rate_limits: dict[str, float] = {}
rate_limits_lock = threading.Lock()

work_queue: queue.Queue[str] = queue.Queue()


def _worker() -> None:
    while True:
        job_id = work_queue.get()
        try:
            with jobs_lock:
                jobs[job_id]["status"] = "processing"
                colors = jobs[job_id].get("colors")
            job_dir = JOBS_DIR / job_id
            process_pdf(str(job_dir / "input.pdf"), str(job_dir / "output.pdf"), colors=colors)
            with jobs_lock:
                jobs[job_id]["status"] = "done"
                jobs[job_id]["completed_at"] = time.time()
        except Exception as exc:
            with jobs_lock:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = str(exc)
        finally:
            work_queue.task_done()


def _cleanup_worker() -> None:
    while True:
        time.sleep(3600)
        now = time.time()
        with jobs_lock:
            expired = [
                jid for jid, job in jobs.items()
                if job.get("completed_at") and now - job["completed_at"] > JOB_TTL_SECONDS
            ]
            for jid in expired:
                shutil.rmtree(JOBS_DIR / jid, ignore_errors=True)
                del jobs[jid]


for _ in range(MAX_WORKERS):
    threading.Thread(target=_worker, daemon=True).start()
threading.Thread(target=_cleanup_worker, daemon=True).start()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).parent / "static" / "index.html").read_text()


@app.post("/upload")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    colors_json: str | None = Form(default=None),
) -> dict:
    ip = request.client.host
    now = time.time()
    with rate_limits_lock:
        last = rate_limits.get(ip, 0.0)
        remaining = RATE_LIMIT_SECONDS - (now - last)
        if remaining > 0:
            raise HTTPException(429, f"Too many requests. Please wait {int(remaining)}s before submitting again.")
        rate_limits[ip] = now

    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")

    content = await file.read()
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(400, f"File too large. Max {MAX_FILE_MB} MB.")

    job_id = str(uuid.uuid4())
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir()
    (job_dir / "input.pdf").write_bytes(content)

    colors = _parse_colors(colors_json) or dict(BOOMWHACKER)

    with jobs_lock:
        jobs[job_id] = {
            "status": "pending",
            "created_at": now,
            "filename": file.filename or "output.pdf",
            "colors": colors,
        }

    work_queue.put(job_id)
    return {"job_id": job_id, "queue_position": work_queue.qsize()}


@app.get("/status/{job_id}")
def status(job_id: str) -> dict:
    with jobs_lock:
        job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")

    queue_position: int | None = None
    if job["status"] == "pending":
        items = list(work_queue.queue)
        if job_id in items:
            queue_position = items.index(job_id) + 1

    return {
        "status": job["status"],
        "queue_position": queue_position,
        "error": job.get("error"),
    }


@app.get("/download/{job_id}")
def download(job_id: str) -> FileResponse:
    with jobs_lock:
        job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    if job["status"] != "done":
        raise HTTPException(400, "Job not complete yet.")
    output = JOBS_DIR / job_id / "output.pdf"
    if not output.exists():
        raise HTTPException(500, "Output file missing.")
    stem = Path(job["filename"]).stem
    return FileResponse(str(output), filename=f"{stem}_colored.pdf", media_type="application/pdf")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
