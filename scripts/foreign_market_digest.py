from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from digest_config import (
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
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
        default=8,
        help="Maximum number of hotspots to keep.",
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
    return parser.parse_args()


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
