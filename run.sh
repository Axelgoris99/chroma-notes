#!/usr/bin/env bash
# Wrapper for chroma-notes that points LD_LIBRARY_PATH at the NVIDIA CUDA
# libraries installed into the project's .venv via pip.
#
# Usage:
#   ./run.sh input/test.pdf output/test.pdf
#   ./run.sh input/*.pdf output/        # if chroma-notes supports multiple inputs

set -euo pipefail

# Resolve project root (directory containing this script), so the script works
# no matter where you call it from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Discover all nvidia/*/lib dirs inside the venv. Glob runs at script time
# so newly-installed nvidia-* packages are picked up automatically.
NVIDIA_LIBS=$(uv run python -c '
import glob, os
paths = glob.glob(".venv/lib/python*/site-packages/nvidia/*/lib")
print(":".join(p for p in paths if os.path.isdir(p)))
')

if [[ -z "$NVIDIA_LIBS" ]]; then
    echo "warning: no nvidia/*/lib dirs found in .venv — falling back to CPU" >&2
else
    export LD_LIBRARY_PATH="$NVIDIA_LIBS:${LD_LIBRARY_PATH:-}"
fi

exec uv run chroma-notes "$@"