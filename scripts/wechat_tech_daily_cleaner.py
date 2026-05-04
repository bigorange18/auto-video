from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup  # pyright: ignore[reportMissingImports]

LOGGER = logging.getLogger("wechat_tech_daily_cleaner")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

TECH_KEYWORDS = {
    "高": ["ai", "agent", "大模型", "芯片", "算力", "云计算", "发布", "融资"],
    "中": ["硬件", "终端", "模型", "开发者", "平台", "企业服务", "互联网"],
}
IMAGE_BLOCKLIST = ("logo", "icon", "avatar", "qrcode", "qr", "banner", "ads")
ARTICLE_SELECTORS = (
    "article",
    ".news-list li",
    ".list-con li",
    ".news-item",
    ".article-item",
    ".post-item",
)
TITLE_SELECTORS = ("h1", "h2", "h3", "a[title]", "a")
SUMMARY_SELECTORS = ("p", ".summary", ".desc", ".article-desc")
TIME_SELECTORS = ("time", ".time", ".date", ".pub-time")
SOURCE_SELECTORS = (".source", ".media", ".from", ".article-source")


@dataclass
class ImageCandidate:
    url: str
    desc: str
    usable: bool


@dataclass
class NewsItem:
    title: str
    source: str
    published_at: str
    url: str
    summary: str
    tags: list[str]
    importance_hint: str
    images: list[ImageCandidate]


@dataclass
class PolicyUpdate:
    title: str
    summary: str


@dataclass
class TomorrowWatch:
    title: str
    summary: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean tech news page into structured JSON for WeChat daily prompt."
    )
    parser.add_argument(
        "--input-url",
        help="Source page URL. Use this or --input-html.",
    )
    parser.add_argument(
        "--input-html",
        type=Path,
        help="Local HTML file path. Use this or --input-url.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for structured JSON.",
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Report date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--topic",
        default="科技板块日报",
        help="Topic name written into output payload.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=12,
        help="Maximum number of cleaned news items to keep before downstream LLM filtering.",
    )
    parser.add_argument(
        "--source-name",
        default="",
        help="Optional source name override.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def validate_args(args: argparse.Namespace) -> None:
    if not args.input_url and not args.input_html:
        raise SystemExit("One of --input-url or --input-html is required.")
    if args.input_url and args.input_html:
        raise SystemExit("Use either --input-url or --input-html, not both.")


def load_html(args: argparse.Namespace) -> tuple[str, str]:
    if args.input_html:
        html = args.input_html.read_text(encoding="utf-8")
        base_url = args.input_url or ""
        return html, base_url

    request = Request(args.input_url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")

    charset = extract_charset(content_type) or "utf-8"
    try:
        html = raw.decode(charset)
    except UnicodeDecodeError:
        html = raw.decode("utf-8", errors="ignore")
    return html, args.input_url


def extract_charset(content_type: str) -> str:
    match = re.search(r"charset=([a-zA-Z0-9_-]+)", content_type, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_title(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^\w\u4e00-\u9fff]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def guess_source(base_url: str, override: str) -> str:
    if override:
        return override
    if not base_url:
        return "Unknown"
    hostname = urlparse(base_url).hostname or ""
    return hostname.replace("www.", "") or "Unknown"


def extract_news_items(html: str, base_url: str, source_name: str, limit: int) -> list[NewsItem]:
    soup = BeautifulSoup(html, "html.parser")
    blocks = find_article_blocks(soup)
    LOGGER.info("candidate blocks found: %s", len(blocks))

    results: list[NewsItem] = []
    seen_titles: set[str] = set()
    default_source = guess_source(base_url, source_name)

    for block in blocks:
        item = parse_news_block(block, base_url=base_url, default_source=default_source)
        if item is None:
            continue

        title_key = normalize_title(item.title)
        if not title_key or title_key in seen_titles:
            continue

        seen_titles.add(title_key)
        results.append(item)
        if len(results) >= limit:
            break

    return results


def find_article_blocks(soup: BeautifulSoup) -> list:
    blocks: list = []
    for selector in ARTICLE_SELECTORS:
        matched = soup.select(selector)
        if len(matched) >= 3:
            blocks = matched
            break
    if blocks:
        return blocks

    links = [node.parent for node in soup.select("a[title]") if node.parent is not None]
    return links[:20]


def parse_news_block(block, base_url: str, default_source: str) -> NewsItem | None:
    title = first_text(block, TITLE_SELECTORS)
    if len(title) < 8:
        return None

    link = extract_link(block, base_url)
    summary = first_text(block, SUMMARY_SELECTORS)
    summary = summary or title
    published_at = first_text(block, TIME_SELECTORS)
    source = first_text(block, SOURCE_SELECTORS) or default_source
    images = extract_images(block, base_url, title)
    tags = infer_tags(title=title, summary=summary)
    importance_hint = infer_importance(title=title, summary=summary)

    return NewsItem(
        title=title,
        source=source,
        published_at=published_at,
        url=link,
        summary=summary,
        tags=tags,
        importance_hint=importance_hint,
        images=images,
    )


def first_text(block, selectors: Iterable[str]) -> str:
    for selector in selectors:
        node = block.select_one(selector)
        if node is None:
            continue
        text = clean_text(node.get_text(" ", strip=True))
        if text:
            return text
    return ""


def extract_link(block, base_url: str) -> str:
    link_node = block.select_one("a[href]")
    if link_node is None:
        return ""
    href = clean_text(link_node.get("href", ""))
    if not href:
        return ""
    return urljoin(base_url, href)


def extract_images(block, base_url: str, fallback_desc: str) -> list[ImageCandidate]:
    results: list[ImageCandidate] = []
    for img in block.select("img[src]")[:3]:
        raw_url = clean_text(img.get("src", ""))
        if not raw_url:
            continue
        image_url = urljoin(base_url, raw_url)
        desc = clean_text(img.get("alt", "")) or fallback_desc
        usable = is_usable_image(image_url, desc)
        results.append(ImageCandidate(url=image_url, desc=desc, usable=usable))
    return dedupe_images(results)


def is_usable_image(url: str, desc: str) -> bool:
    lowered = f"{url} {desc}".lower()
    if any(keyword in lowered for keyword in IMAGE_BLOCKLIST):
        return False
    return url.startswith("http://") or url.startswith("https://")


def dedupe_images(images: list[ImageCandidate]) -> list[ImageCandidate]:
    deduped: list[ImageCandidate] = []
    seen: set[str] = set()
    for image in images:
        if image.url in seen:
            continue
        seen.add(image.url)
        deduped.append(image)
    return deduped


def infer_tags(title: str, summary: str) -> list[str]:
    text = f"{title} {summary}".lower()
    candidates = {
        "AI": ("ai", "agent", "大模型", "模型"),
        "芯片": ("芯片", "半导体", "算力", "gpu"),
        "云计算": ("云", "云计算", "api", "开发者平台"),
        "消费电子": ("手机", "耳机", "硬件", "终端"),
        "企业服务": ("企业", "saas", "工作流", "知识库"),
        "商业化": ("融资", "营收", "付费", "商业化"),
    }
    tags = [tag for tag, keywords in candidates.items() if any(keyword in text for keyword in keywords)]
    return tags[:4]


def infer_importance(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    for level, keywords in TECH_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return level
    return "低"


def build_payload(
    *,
    date: str,
    topic: str,
    news_items: list[NewsItem],
    source_name: str,
) -> dict:
    payload = {
        "date": date,
        "topic": topic,
        "news_items": [serialize_news_item(item) for item in news_items],
        "market_data": {
            "a_share": [],
            "us_stock": [],
        },
        "policy_updates": [],
        "tomorrow_watch": [],
        "meta": {
            "source_count": len(news_items),
            "dedup_note": "按标准化标题做基础去重；后续可增加链接和事件聚类去重。",
            "image_policy": "仅 usable=true 的图片适合继续传给模型作为候选配图。",
            "language": "zh-CN",
            "source_name": source_name or "",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
    }
    return payload


def serialize_news_item(item: NewsItem) -> dict:
    data = asdict(item)
    data["images"] = [asdict(image) for image in item.images]
    return data


def write_output(output_path: Path, payload: dict) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)
    validate_args(args)

    html, base_url = load_html(args)
    news_items = extract_news_items(
        html,
        base_url=base_url,
        source_name=args.source_name,
        limit=args.limit,
    )

    payload = build_payload(
        date=args.date,
        topic=args.topic,
        news_items=news_items,
        source_name=args.source_name or guess_source(base_url, args.source_name),
    )
    write_output(args.output, payload)
    LOGGER.info("wrote %s cleaned items to %s", len(news_items), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())