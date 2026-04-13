#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(readlink -f "$SCRIPT_DIR/..")"
ENV_FILE="${DIGEST_ENV_FILE:-$PROJECT_ROOT/.env.digest}"
PYTHON_BIN="${PYTHON_BIN:-/home/orange/miniconda3/bin/python3}"
LOG_FILE="${DIGEST_LOG_FILE:-$PROJECT_ROOT/cron.log}"

if [[ ! -f "$ENV_FILE" ]]; then
  printf 'Missing env file: %s\n' "$ENV_FILE" >&2
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  printf 'Python not executable: %s\n' "$PYTHON_BIN" >&2
  exit 1
fi

set -a
. "$ENV_FILE"
set +a

mkdir -p "$PROJECT_ROOT/output"
touch "$LOG_FILE"

"$PYTHON_BIN" "$PROJECT_ROOT/scripts/foreign_market_digest.py" \
  --hours "${DIGEST_HOURS:-24}" \
  --limit "${DIGEST_LIMIT:-10}" \
  --pushplus-token "${PUSHPLUS_TOKEN:-}" \
  --feishu-webhook "${FEISHU_WEBHOOK_URL:-}" \
  --wechat-app-id "${WECHAT_APP_ID:-}" \
  --wechat-app-secret "${WECHAT_APP_SECRET:-}" \
  --wechat-author "${WECHAT_AUTHOR:-Auto Video}" \
  >> "$LOG_FILE" 2>&1
