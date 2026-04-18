#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate
mkdocs build --clean

echo "Build complete: $(pwd)/site"
