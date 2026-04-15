#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(readlink -f "$SCRIPT_DIR/..")"
ENV_FILE="${DIGEST_ENV_FILE:-$PROJECT_ROOT/.env.digest}"
PYTHON_BIN="${PYTHON_BIN:-/home/orange/miniconda3/bin/python3}"
LOG_DIR="${DIGEST_LOG_DIR:-$PROJECT_ROOT/logs}"
TODAY="$(date +%F)"
LOG_FILE="${DIGEST_LOG_FILE:-$LOG_DIR/digest-$TODAY.log}"

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
mkdir -p "$LOG_DIR"
touch "$LOG_FILE"
export DIGEST_LOG_FILE="$LOG_FILE"

CMD=(
  "$PYTHON_BIN" "$PROJECT_ROOT/scripts/foreign_market_digest.py"
  --hours "${DIGEST_HOURS:-24}"
  --limit "${DIGEST_LIMIT:-10}"
  --select-limit "${DIGEST_SELECT_LIMIT:-5}"
  --pushplus-token "${PUSHPLUS_TOKEN:-}"
  --feishu-webhook "${FEISHU_WEBHOOK_URL:-}"
  --wechat-app-id "${WECHAT_APP_ID:-}"
  --wechat-app-secret "${WECHAT_APP_SECRET:-}"
  --wechat-author "${WECHAT_AUTHOR:-Auto Video}"
)

if [[ "${DIGEST_LLM_ENABLED:-0}" == "1" ]]; then
  LLM_PROVIDER_VALUE="${LLM_PROVIDER:-${DIGEST_LLM_PROVIDER:-openai}}"
  LLM_BASE_URL_VALUE="${LLM_BASE_URL:-}"
  LLM_API_KEY_VALUE="${LLM_API_KEY:-}"
  LLM_MODEL_VALUE="${LLM_MODEL:-}"

  if [[ -z "$LLM_BASE_URL_VALUE" ]]; then
    if [[ "$LLM_PROVIDER_VALUE" == "qwen" ]]; then
      LLM_BASE_URL_VALUE="${DASHSCOPE_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
    elif [[ "$LLM_PROVIDER_VALUE" == "deepseek" ]]; then
      LLM_BASE_URL_VALUE="${DEEPSEEK_BASE_URL:-https://api.deepseek.com/v1}"
    else
      LLM_BASE_URL_VALUE="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
    fi
  fi

  if [[ -z "$LLM_API_KEY_VALUE" ]]; then
    if [[ "$LLM_PROVIDER_VALUE" == "qwen" ]]; then
      LLM_API_KEY_VALUE="${DASHSCOPE_API_KEY:-${QWEN_API_KEY:-}}"
    elif [[ "$LLM_PROVIDER_VALUE" == "deepseek" ]]; then
      LLM_API_KEY_VALUE="${DEEPSEEK_API_KEY:-${DEEPSEEK_KEY:-}}"
    else
      LLM_API_KEY_VALUE="${OPENAI_API_KEY:-}"
    fi
  fi

  if [[ -z "$LLM_MODEL_VALUE" ]]; then
    if [[ "$LLM_PROVIDER_VALUE" == "qwen" ]]; then
      LLM_MODEL_VALUE="${QWEN_MODEL:-qwen-plus}"
    elif [[ "$LLM_PROVIDER_VALUE" == "deepseek" ]]; then
      LLM_MODEL_VALUE="${DEEPSEEK_MODEL:-deepseek-chat}"
    else
      LLM_MODEL_VALUE="${OPENAI_MODEL:-gpt-4o-mini}"
    fi
  fi

  CMD+=(
    --llm-enabled
    --llm-provider "$LLM_PROVIDER_VALUE"
    --llm-base-url "$LLM_BASE_URL_VALUE"
    --llm-api-key "$LLM_API_KEY_VALUE"
    --llm-model "$LLM_MODEL_VALUE"
    --llm-timeout "${LLM_TIMEOUT:-25}"
  )
fi

printf '[KEY] Log file: %s\n' "$LOG_FILE"
"${CMD[@]}"
