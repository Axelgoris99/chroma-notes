#!/usr/bin/env bash
set -e

SITE="$(python -c 'import site; print(site.getsitepackages()[0])')"

NVIDIA_LIBS="$(find "$SITE/nvidia" -maxdepth 2 -name lib -type d 2>/dev/null | tr '\n' ':')"

export LD_LIBRARY_PATH="${NVIDIA_LIBS}${LD_LIBRARY_PATH}"

exec uvicorn web.app:app --host 0.0.0.0 --port 8000 --workers 1
