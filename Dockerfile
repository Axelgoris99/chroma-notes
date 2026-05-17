FROM python:3.11-slim

# System libs required by OpenCV and OpenMP
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (layer cached unless pyproject/lockfile change)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copy source
COPY src/ ./src/
COPY web/ ./web/
COPY scripts/ ./scripts/

# Install the project itself
RUN uv sync --frozen

# Download oemer ONNX checkpoints (~200 MB, cached as its own layer)
RUN uv run python scripts/download_models.py

VOLUME ["/app/jobs"]
EXPOSE 8000

# Single uvicorn worker — we manage our own thread pool for job processing
CMD ["uv", "run", "uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
