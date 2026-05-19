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