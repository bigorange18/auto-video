#!/usr/bin/env bash
set -euo pipefail

WORK_DIR="${WORK_DIR:-/mnt/f/fun_project/auto-video}"
ENV_FILE="${ENV_FILE:-$WORK_DIR/.diag.env}"
VENV_ACTIVATE="${VENV_ACTIVATE:-$WORK_DIR/.venv/bin/activate}"
WECHAT_TECH_DIR="$WORK_DIR/wechat_tech"
OUTPUT_DIR="${REPORT_OUTPUT_DIR:-$WORK_DIR/output/wechat-tech}"
RUN_DATE="${RUN_DATE:-$(date +%F)}"
SOURCE_URL="${WECHAT_TECH_SOURCE_URL:-https://news.10jqka.com.cn/}"
SOURCE_NAME="${WECHAT_TECH_SOURCE_NAME:-同花顺科技}"
ITEM_LIMIT="${WECHAT_TECH_ITEM_LIMIT:-20}"

mkdir -p "$OUTPUT_DIR"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

if [[ -f "$VENV_ACTIVATE" ]]; then
  # shellcheck disable=SC1090
  source "$VENV_ACTIVATE"
fi

CLEANED_JSON="$OUTPUT_DIR/cleaned-$RUN_DATE.json"
PROMPT_TXT="$OUTPUT_DIR/prompt-$RUN_DATE.txt"
DRAFT_MD="$OUTPUT_DIR/draft-$RUN_DATE.md"
RAW_LLM_JSON="$OUTPUT_DIR/raw-llm-$RUN_DATE.json"

python "$WECHAT_TECH_DIR/wechat_tech_daily_cleaner.py" \
  --input-url "$SOURCE_URL" \
  --output "$CLEANED_JSON" \
  --source-name "$SOURCE_NAME" \
  --limit "$ITEM_LIMIT"

python "$WECHAT_TECH_DIR/render_wechat_tech_prompt.py" \
  --input-json "$CLEANED_JSON" \
  --output "$PROMPT_TXT"

python "$WECHAT_TECH_DIR/generate_wechat_tech_draft.py" \
  --input-prompt "$PROMPT_TXT" \
  --output "$DRAFT_MD" \
  --save-raw-response "$RAW_LLM_JSON" \
  --llm-provider "${LLM_PROVIDER:-deepseek}" \
  --llm-api-key "${LLM_API_KEY:-}" \
  --llm-base-url "${LLM_BASE_URL:-https://api.deepseek.com/v1}" \
  --llm-model "${LLM_MODEL:-deepseek-chat}"

# Publish to WeChat Official Account drafts
if [[ -n "${AppID:-}" && -n "${AppSecret:-}" && -n "${WECHAT_THUMB_MEDIA_ID:-}" ]]; then
  echo "publishing to wechat drafts..."
  python "$WECHAT_TECH_DIR/publish_wechat_tech_draft.py" \
    --input-md "$DRAFT_MD" \
    --app-id "${AppID:-}" \
    --app-secret "${AppSecret:-}" \
    --author "${WECHAT_AUTHOR:-科技日报}" \
    --thumb-media-id "${WECHAT_THUMB_MEDIA_ID:-}"
fi

echo "cleaned_json=$CLEANED_JSON"
echo "prompt_txt=$PROMPT_TXT"
echo "draft_md=$DRAFT_MD"
echo "raw_llm_json=$RAW_LLM_JSON"
