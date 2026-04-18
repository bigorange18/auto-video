#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

# Optional mirrors for mainland network environments.
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
PIP_TIMEOUT="${PIP_TIMEOUT:-120}"

pip install -r requirements.txt -i "$PIP_INDEX_URL" --timeout "$PIP_TIMEOUT"

echo "Bootstrap complete."
echo "Run: source .venv/bin/activate && mkdocs serve -a 0.0.0.0:8008"
