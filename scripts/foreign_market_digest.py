from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from digest_config import (
    DEFAULT_DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_LLM_CONFIG,
    DEFAULT_OPENAI_BASE_URL,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    DEFAULT_QWEN_BASE_URL,
    DEFAULT_QWEN_MODEL,
    DEFAULT_WECHAT_AUTHOR,
)
from digest_logging import setup_logging
from foreign_market_digest_service import ForeignMarketDigestService


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for digest execution."""
    parser = argparse.ArgumentParser(
        description="Fetch foreign market hotspots and generate Chinese copywriting."
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Only keep articles published within this many hours.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of candidate hotspots to collect before final selection.",
    )
    parser.add_argument(
        "--select-limit",
        type=int,
        default=5,
        help="Maximum number of hotspots kept after LLM scoring.",
    )
    parser.add_argument(
        "--hot-limit",
        type=int,
        default=10,
        help="Maximum number of hot topics per platform to keep.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help="Output path for structured JSON.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=DEFAULT_OUTPUT_MD,
        help="Output path for generated markdown copy.",
    )
    parser.add_argument(
        "--feishu-webhook",
        default=os.getenv("FEISHU_WEBHOOK_URL", ""),
        help="Optional Feishu bot webhook URL.",
    )
    parser.add_argument(
        "--pushplus-token",
        default=os.getenv("PUSHPLUS_TOKEN", ""),
        help="Optional PushPlus token for WeChat delivery.",
    )
    parser.add_argument(
        "--wechat-app-id",
        default=os.getenv("WECHAT_APP_ID", ""),
        help="Optional WeChat Official Account app id.",
    )
    parser.add_argument(
        "--wechat-app-secret",
        default=os.getenv("WECHAT_APP_SECRET", ""),
        help="Optional WeChat Official Account app secret.",
    )
    parser.add_argument(
        "--wechat-author",
        default=os.getenv("WECHAT_AUTHOR", DEFAULT_WECHAT_AUTHOR),
        help="WeChat draft author name.",
    )
    parser.add_argument(
        "--wechat-thumb-media-id",
        default=os.getenv("WECHAT_THUMB_MEDIA_ID", ""),
        help="Permanent image media_id used as WeChat article cover.",
    )
    parser.add_argument(
        "--strict-wechat",
        action="store_true",
        help="Exit with error when WeChat draft creation fails.",
    )
    parser.add_argument(
        "--strict-fetch",
        action="store_true",
        help="Exit with error when no article can be fetched.",
    )
    parser.add_argument(
        "--llm-enabled",
        action="store_true",
        help="Enable LLM-based content refinement for summary and copywriting.",
    )
    parser.add_argument(
        "--llm-provider",
        choices=("openai", "qwen", "deepseek"),
        default=_resolve_default_llm_provider(),
        help="LLM provider preset used to resolve defaults.",
    )
    parser.add_argument(
        "--llm-base-url",
        default=_resolve_default_llm_base_url(),
        help="LLM API base URL (OpenAI-compatible).",
    )
    parser.add_argument(
        "--llm-api-key",
        default=_resolve_default_llm_api_key(),
        help="LLM API key.",
    )
    parser.add_argument(
        "--llm-model",
        default=_resolve_default_llm_model(),
        help="LLM model name used for copy refinement.",
    )
    parser.add_argument(
        "--llm-config",
        type=Path,
        default=Path(os.getenv("LLM_CONFIG_PATH", str(DEFAULT_LLM_CONFIG))),
        help="Path to external LLM scoring/copywriting config JSON.",
    )
    parser.add_argument(
        "--llm-timeout",
        type=int,
        default=int(os.getenv("LLM_TIMEOUT", "25")),
        help="LLM API request timeout in seconds.",
    )
    return parser.parse_args()


def _resolve_default_llm_provider() -> str:
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider in {"openai", "qwen", "deepseek"}:
        return provider
    if os.getenv("DASHSCOPE_API_KEY", "").strip() or os.getenv("QWEN_API_KEY", "").strip():
        return "qwen"
    if os.getenv("DEEPSEEK_API_KEY", "").strip() or os.getenv("DEEPSEEK_KEY", "").strip():
        return "deepseek"
    return "openai"


def _resolve_default_llm_base_url() -> str:
    explicit = os.getenv("LLM_BASE_URL", "").strip()
    if explicit:
        return explicit

    provider = _resolve_default_llm_provider()
    if provider == "qwen":
        return os.getenv("DASHSCOPE_BASE_URL", "").strip() or DEFAULT_QWEN_BASE_URL
    if provider == "deepseek":
        return os.getenv("DEEPSEEK_BASE_URL", "").strip() or DEFAULT_DEEPSEEK_BASE_URL
    return os.getenv("OPENAI_BASE_URL", "").strip() or DEFAULT_OPENAI_BASE_URL


def _resolve_default_llm_api_key() -> str:
    explicit = os.getenv("LLM_API_KEY", "").strip()
    if explicit:
        return explicit

    provider = _resolve_default_llm_provider()
    if provider == "qwen":
        return os.getenv("DASHSCOPE_API_KEY", "").strip() or os.getenv("QWEN_API_KEY", "").strip()
    if provider == "deepseek":
        return os.getenv("DEEPSEEK_API_KEY", "").strip() or os.getenv("DEEPSEEK_KEY", "").strip()
    return os.getenv("OPENAI_API_KEY", "").strip()


def _resolve_default_llm_model() -> str:
    explicit = os.getenv("LLM_MODEL", "").strip()
    if explicit:
        return explicit

    provider = _resolve_default_llm_provider()
    if provider == "qwen":
        return os.getenv("QWEN_MODEL", "").strip() or DEFAULT_QWEN_MODEL
    if provider == "deepseek":
        return os.getenv("DEEPSEEK_MODEL", "").strip() or DEFAULT_DEEPSEEK_MODEL
    return os.getenv("OPENAI_MODEL", "").strip() or DEFAULT_OPENAI_MODEL


def main() -> int:
    """Run digest generation flow."""
    log_file = setup_logging()
    logging.getLogger("digest").info("logging initialized: %s", log_file)
    args = parse_args()
    service = ForeignMarketDigestService(args)
    try:
        return service.run()
    except Exception:
        logging.getLogger("digest").exception("digest run failed")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
