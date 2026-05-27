# Chroma Notes

Color-code every note in a sheet music PDF using [Boomwhacker](https://en.wikipedia.org/wiki/Boomwhacker) colors.

| Note | Solfège | Color |
|------|---------|-------|
| C | Do | Red |
| D | Ré | Orange |
| E | Mi | Yellow |
| F | Fa | Lime green |
| G | Sol | Dark green |
| A | La | Purple |
| B | Si | Pink |

Powered by [oemer](https://github.com/BreezeWhite/oemer) for optical music recognition.


Warning: The demo takes 5+ minutes for a 1 page pdf. It is running on a cheap 4vCpu VPS.
But, there's a demo running at: <https://chroma.goris.live>


---

## Local CLI

**Requirements:** Python 3.11+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/axelgoris99/chroma-notes
cd chroma-notes
uv sync
uv run chroma-notes input.pdf output.pdf
```

> On first run oemer will download its model checkpoints (~200 MB).

### GPU acceleration (optional)

If you have an NVIDIA GPU, processing drops from ~5 min/page to a few seconds. The nvidia CUDA libraries live in a separate dependency group so they don't bloat the production Docker image.

```bash
uv sync --group gpu   # installs nvidia-cublas/cudnn/cufft/cuda-runtime into the venv
```

Then use `start.sh` instead of `uv run` to launch the web server — it sets `LD_LIBRARY_PATH` to point at those pip-installed libs before starting uvicorn (the dynamic linker won't find them otherwise):

```bash
uv run ./start.sh
```

`uv run chroma-notes …` (the CLI) still works fine on CPU without any of this.

---

## GPU via Modal (optional)

Setting `USE_MODAL=1` offloads the OMR step to a [Modal](https://modal.com) GPU function instead of running it locally. This is how the public demo at <https://chroma.goris.live> avoids a 6 GB GPU dependency in the server container.

You also need to supply your Modal credentials:

```
USE_MODAL=1
MODAL_TOKEN_ID=<your-token-id>
MODAL_TOKEN_SECRET=<your-token-secret>
```

If the Modal call fails for any reason the pipeline falls back to local CPU automatically.

---

## Web app with Docker

Build and run locally:

```bash
docker compose up --build
```

Open http://localhost:8000, upload a PDF, download the colored result.

---

## Web app from GHCR (pre-built image)

Pull the image built by GitHub Actions — no local build needed:

```bash
docker compose pull && docker compose up -d
```

The `docker-compose.yml` already points to `ghcr.io/axelgoris99/chroma-notes:latest`.

---

## Updating

```bash
git pull
docker compose pull && docker compose up -d
```

## FAQ

"It does not work".

Oof, tough one buddy. Unfortunately many things can go wrong, such as:

- Oemer not recognizing the clef or the note which will lead to the wrong colors
- The queue system messing up if you use the demo version at <chroma.goris.live/>
- The server is busy with other stuff.