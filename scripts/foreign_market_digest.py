from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import quote
from urllib.request import Request, urlopen


USER_AGENT = "Mozilla/5.0 (compatible; auto-video/1.0; +https://github.com/)"
DEFAULT_OUTPUT_JSON = Path("output/foreign_market_hotspots.json")
DEFAULT_OUTPUT_MD = Path("output/foreign_market_copy.md")
GOOGLE_NEWS_BASE = "https://news.google.com/rss/search"
PUSHPLUS_URL = "https://www.pushplus.plus/send"
WECHAT_ACCESS_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
WECHAT_ADD_DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
WECHAT_ADD_MATERIAL_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"
DEFAULT_WECHAT_AUTHOR = "Auto Video"
DEFAULT_WECHAT_COVER_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAlgAAADICAIAAAC7/QjhAAAACXBIWXMAAAsSAAALEgHS3X78AAAF"
    "hUlEQVR4nO3VMQ0AAAjDMOZfNHIx4C8E2XQK6JqZmZkBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP4GAb8AAe2y"
    "4UAAAAAASUVORK5CYII="
)

FEEDS = [
    {
        "label": "US",
        "url": "https://finance.yahoo.com/rss/topstories",
        "weight": 3,
    },
    {
        "label": "US",
        "url": "https://www.investing.com/rss/news_25.rss",
        "weight": 3,
    },
    {
        "label": "Europe",
        "query": '("European stocks" OR "STOXX 600" OR FTSE OR DAX) when:1d',
        "weight": 2,
    },
    {
        "label": "Asia",
        "query": '("Asian stocks" OR Nikkei OR Hang Seng OR "MSCI Asia") when:1d',
        "weight": 2,
    },
    {
        "label": "Global",
        "query": '(NASDAQ OR NYSE OR "S&P 500" OR "Dow Jones") when:1d',
        "weight": 2,
    },
    {
        "label": "Global",
        "url": "https://www.investing.com/rss/news_285.rss",
        "weight": 2,
    },
]

THEMES = [
    ("利率与美联储", ["fed", "rate", "rates", "treasury", "bond", "yield", "powell"]),
    ("科技与芯片", ["ai", "chip", "chips", "semiconductor", "nvidia", "tsmc", "tech"]),
    ("财报与业绩", ["earnings", "profit", "revenue", "guidance", "quarter", "results"]),
    ("通胀与宏观", ["inflation", "cpi", "ppi", "payrolls", "gdp", "recession", "macro"]),
    ("能源与大宗", ["oil", "crude", "gas", "gold", "commodity", "opec"]),
    ("监管与关税", ["tariff", "regulation", "antitrust", "ban", "sanction", "policy"]),
    ("欧洲市场", ["europe", "euro", "stoxx", "ftse", "dax", "ecb"]),
    ("亚洲市场", ["asia", "japan", "china", "hong kong", "nikkei", "hang seng"]),
]

MAJOR_SOURCES = {
    "Reuters",
    "Bloomberg",
    "CNBC",
    "Financial Times",
    "MarketWatch",
    "The Wall Street Journal",
    "Barron's",
    "Yahoo Finance",
}


@dataclass
class Article:
    title: str
    link: str
    source: str
    published_at: str
    age_hours: float
    region: str
    theme: str
    score: int
    rationale: str


def build_rss_url(query: str) -> str:
    encoded_query = quote(query)
    return f"{GOOGLE_NEWS_BASE}?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def summarize_payload(payload: str, limit: int = 160) -> str:
    compact = re.sub(r"\s+", " ", payload).strip()
    if not compact:
        return "<empty response>"
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def split_title_and_source(raw_title: str, rss_source: str) -> tuple[str, str]:
    if rss_source:
        return raw_title, rss_source
    parts = [part.strip() for part in raw_title.rsplit(" - ", 1)]
    if len(parts) == 2 and 1 < len(parts[1]) <= 40:
        return parts[0], parts[1]
    return raw_title, rss_source or "Unknown"


def normalize_title(title: str) -> str:
    lowered = title.lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def match_theme(text: str) -> tuple[str, int]:
    lowered = text.lower()
    best_theme = "市场波动"
    best_hits = 0
    for theme, keywords in THEMES:
        hits = sum(1 for keyword in keywords if keyword in lowered)
        if hits > best_hits:
            best_theme = theme
            best_hits = hits
    return best_theme, best_hits


def build_rationale(theme: str, age_hours: float, source: str, hit_count: int) -> str:
    reasons: list[str] = [f"主线偏向{theme}"]
    if hit_count >= 2:
        reasons.append("标题触发多个市场关键词")
    if age_hours <= 8:
        reasons.append("发布时间较近")
    if source in MAJOR_SOURCES:
        reasons.append(f"来源为{source}")
    return "，".join(reasons)


def score_article(region_weight: int, age_hours: float, hit_count: int, source: str) -> int:
    score = region_weight * 10 + hit_count * 6
    if age_hours <= 4:
        score += 8
    elif age_hours <= 12:
        score += 5
    elif age_hours <= 24:
        score += 2
    if source in MAJOR_SOURCES:
        score += 3
    return score


def collect_articles(hours: int) -> list[Article]:
    now = datetime.now(timezone.utc)
    deduped: dict[str, Article] = {}
    failures: list[str] = []

    for feed in FEEDS:
        url = feed.get("url") or build_rss_url(feed["query"])
        try:
            payload = fetch_text(url)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{feed['label']}: {exc}")
            continue

        if not payload.strip():
            failures.append(f"{feed['label']}: empty RSS response from {url}")
            continue

        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            snippet = summarize_payload(payload)
            failures.append(
                f"{feed['label']}: invalid RSS payload from {url}: {exc}; body={snippet}"
            )
            continue

        for item in root.findall("./channel/item"):
            raw_title = clean_text(item.findtext("title"))
            if not raw_title:
                continue

            raw_source = clean_text(item.findtext("source") or item.findtext("author"))
            title, source = split_title_and_source(raw_title, raw_source)
            published = parse_datetime(item.findtext("pubDate"))
            if published is None:
                continue

            age_hours = (now - published).total_seconds() / 3600
            if age_hours > hours:
                continue

            link = clean_text(item.findtext("link"))
            theme, hit_count = match_theme(f"{title} {source}")
            score = score_article(feed["weight"], age_hours, hit_count, source)
            article = Article(
                title=title,
                link=link,
                source=source,
                published_at=published.isoformat(),
                age_hours=round(age_hours, 1),
                region=feed["label"],
                theme=theme,
                score=score,
                rationale=build_rationale(theme, age_hours, source, hit_count),
            )

            dedupe_key = normalize_title(title)
            current = deduped.get(dedupe_key)
            if current is None or article.score > current.score:
                deduped[dedupe_key] = article

    if not deduped and failures:
        raise RuntimeError(" | ".join(failures))

    return sorted(deduped.values(), key=lambda article: (-article.score, article.age_hours, article.title))


def top_themes(articles: Iterable[Article], limit: int = 3) -> list[str]:
    counts: dict[str, int] = {}
    for article in articles:
        counts[article.theme] = counts.get(article.theme, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [name for name, _ in ranked[:limit]]


def build_summary(articles: list[Article], hours: int) -> str:
    themes = top_themes(articles)
    theme_text = "、".join(themes) if themes else "市场波动"
    return f"先说结论，过去{hours}小时海外市场不是普涨普跌那么简单，真正带节奏的是{theme_text}。今天谁能抓住这几条主线，谁就更容易看懂盘面情绪往哪边走。"


def build_headline_candidates(themes: list[str]) -> list[str]:
    theme_text = "、".join(themes[:2]) if themes else "海外股市"
    return [
        f"隔夜外盘真正的主线出来了，{theme_text}正在带节奏",
        f"别只看指数涨跌，{theme_text}才是海外市场核心变量",
        f"开盘前必须先看这几条，海外资金正在重押这些方向",
    ]


def build_short_video_script(articles: list[Article], hours: int) -> str:
    themes = top_themes(articles)
    top_items = articles[:3]
    lead = f"先说判断，过去{hours}小时海外市场最值得盯的，不是单纯指数波动，而是{'、'.join(themes) if themes else '市场波动'}这几条线在带节奏。"
    points = []
    for index, article in enumerate(top_items, start=1):
        region_text = {
            "US": "美股",
            "Europe": "欧股",
            "Asia": "亚太市场",
        }.get(article.region, article.region)
        points.append(
            f"第{index}条，{region_text}这边最强的交易方向是{article.theme}，代表消息是《{article.title}》，来源是{article.source}，这说明资金已经开始围绕这条线做选择。"
        )
    close = "所以今天看外盘，重点不是市场有没有波动，而是哪条主线最有持续性。做口播时，先甩结论，再拆主线，最后落到资金选择，这样节奏会更强，观点也更像真正的爆款盘前解读。"
    return "".join([lead, *points, close])


def build_social_post(articles: list[Article], hours: int) -> str:
    themes = top_themes(articles)
    focus = "、".join(themes) if themes else "市场波动"
    sources = "、".join(sorted({article.source for article in articles[:5]}))
    return (
        f"盘前先给结论：过去{hours}小时，海外市场真正带节奏的方向是{focus}。"
        f"目前高频信息主要来自{sources}，接下来重点不是看热闹，而是看这些主线能不能继续扩散到指数、科技龙头和风险偏好上。"
    )


def build_feishu_message(payload: dict) -> dict:
    articles = payload["articles"][:3]
    article_blocks = []
    for index, article in enumerate(articles, start=1):
        article_blocks.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**{index}. {article['theme']} | {article['region']}**\n"
                        f"{article['title']}\n"
                        f"热度分：`{article['score']}` | 来源：{article['source']}"
                    ),
                },
            }
        )

    headline_text = "\n".join(
        f"- {title}" for title in payload["headline_candidates"][:2]
    )

    return {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True,
            },
            "header": {
                "template": "red",
                "title": {
                    "tag": "plain_text",
                    "content": "海外热点股市日报",
                },
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**结论先行**\n{payload['summary']}",
                    },
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**统计窗口**\n近 {payload['window_hours']} 小时",
                            },
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**生成时间**\n{payload['generated_at']}",
                            },
                        },
                    ],
                },
                {
                    "tag": "hr",
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**标题建议**\n{headline_text}",
                    },
                },
                {
                    "tag": "hr",
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**热点清单**",
                    },
                },
                *article_blocks,
                {
                    "tag": "hr",
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**社媒文案**\n{payload['social_post']}",
                    },
                },
            ],
        },
    }


def post_json(url: str, payload: dict) -> None:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        response.read()


def post_json_and_read(url: str, payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def create_multipart_body(fields: dict[str, str], file_field: str, file_name: str, file_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = f"----AutoVideoBoundary{datetime.now(timezone.utc).timestamp():.0f}"
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{file_name}"\r\n'.encode("utf-8")
    )
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
    body.extend(file_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), boundary


def post_multipart(url: str, fields: dict[str, str], file_field: str, file_name: str, file_bytes: bytes, content_type: str) -> dict:
    body, boundary = create_multipart_body(fields, file_field, file_name, file_bytes, content_type)
    request = Request(
        url,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def push_to_feishu(payload: dict, webhook_url: str) -> None:
    try:
        post_json(webhook_url, build_feishu_message(payload))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Feishu push failed with status {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Feishu push failed: {exc.reason}") from exc


def build_pushplus_payload(payload: dict, token: str) -> dict:
    markdown_lines = [
        f"# 海外热点股市日报",
        "",
        "## 结论",
        f"> {payload['summary']}",
        "",
        "## 标题",
    ]
    for title in payload["headline_candidates"][:3]:
        markdown_lines.append(f"- {title}")
    markdown_lines.extend(["", "## 热点"])
    for index, article in enumerate(payload["articles"][:5], start=1):
        markdown_lines.append(
            f"{index}. **[{article['region']}/{article['theme']}]** {article['title']}"
        )
        markdown_lines.append(
            f"   - 热度分：`{article['score']}` | 来源：{article['source']}"
        )
    markdown_lines.extend(["", "## 社媒文案", payload["social_post"]])
    return {
        "token": token,
        "title": "海外热点股市日报",
        "content": "\n".join(markdown_lines),
        "template": "markdown",
    }


def push_to_pushplus(payload: dict, token: str) -> None:
    try:
        post_json(PUSHPLUS_URL, build_pushplus_payload(payload, token))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"PushPlus push failed with status {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"PushPlus push failed: {exc.reason}") from exc


def get_wechat_access_token(app_id: str, app_secret: str) -> str:
    url = f"{WECHAT_ACCESS_TOKEN_URL}?grant_type=client_credential&appid={quote(app_id)}&secret={quote(app_secret)}"
    response = fetch_json(url)
    access_token = response.get("access_token")
    if access_token:
        return access_token
    raise RuntimeError(f"WeChat access token failed: {response}")


def build_wechat_cover_bytes() -> bytes:
    return base64.b64decode(DEFAULT_WECHAT_COVER_PNG_BASE64)


def upload_wechat_cover(access_token: str) -> str:
    url = f"{WECHAT_ADD_MATERIAL_URL}?access_token={quote(access_token)}&type=image"
    response = post_multipart(
        url,
        fields={},
        file_field="media",
        file_name="market-cover.png",
        file_bytes=build_wechat_cover_bytes(),
        content_type="image/png",
    )
    media_id = response.get("media_id")
    if media_id:
        return media_id
    raise RuntimeError(f"WeChat cover upload failed: {response}")


def build_wechat_article_content(payload: dict) -> str:
    parts = [
        f"<h1>{html_escape('海外热点股市日报')}</h1>",
        f"<p><strong>结论：</strong>{html_escape(payload['summary'])}</p>",
        "<h2>标题建议</h2>",
        "<ul>",
    ]
    for title in payload["headline_candidates"][:3]:
        parts.append(f"<li>{html_escape(title)}</li>")
    parts.extend(["</ul>", "<h2>热点清单</h2>"])
    for index, article in enumerate(payload["articles"][:5], start=1):
        parts.append(
            f"<p><strong>{index}. [{html_escape(article['region'])}/{html_escape(article['theme'])}]</strong> {html_escape(article['title'])}<br/>"
            f"热度分：{article['score']} | 来源：{html_escape(article['source'])}<br/>"
            f"<a href=\"{html_escape(article['link'])}\">查看原文</a></p>"
        )
    parts.extend(
        [
            "<h2>社媒文案</h2>",
            f"<p>{html_escape(payload['social_post'])}</p>",
        ]
    )
    return "".join(parts)


def build_wechat_draft_payload(payload: dict, author: str, thumb_media_id: str) -> dict:
    return {
        "articles": [
            {
                "title": "海外热点股市日报",
                "author": author,
                "digest": payload["summary"],
                "content": build_wechat_article_content(payload),
                "content_source_url": "",
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }
        ]
    }


def create_wechat_draft(payload: dict, app_id: str, app_secret: str, author: str) -> str:
    access_token = get_wechat_access_token(app_id, app_secret)
    thumb_media_id = upload_wechat_cover(access_token)
    url = f"{WECHAT_ADD_DRAFT_URL}?access_token={quote(access_token)}"
    response = post_json_and_read(url, build_wechat_draft_payload(payload, author, thumb_media_id))
    media_id = response.get("media_id")
    if media_id:
        return media_id
    raise RuntimeError(f"WeChat draft creation failed: {response}")


def build_payload(articles: list[Article], hours: int, source_urls: list[str]) -> dict:
    themes = top_themes(articles)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": hours,
        "source_urls": source_urls,
        "themes": themes,
        "summary": build_summary(articles, hours),
        "headline_candidates": build_headline_candidates(themes),
        "short_video_script": build_short_video_script(articles, hours),
        "social_post": build_social_post(articles, hours),
        "articles": [asdict(article) for article in articles],
    }


def build_markdown(payload: dict) -> str:
    lines = [
        "# 海外热点股市信息日报",
        "",
        f"生成时间：{payload['generated_at']}",
        f"统计窗口：近 {payload['window_hours']} 小时",
        "",
        "## 一句话概览",
        payload["summary"],
        "",
        "## 标题建议",
    ]

    for title in payload["headline_candidates"]:
        lines.append(f"- {title}")

    lines.extend(["", "## 短视频口播文案", payload["short_video_script"], "", "## 社媒短文案", payload["social_post"], "", "## 热点清单"])

    for index, article in enumerate(payload["articles"], start=1):
        lines.append(f"{index}. [{article['theme']}] {article['title']}")
        lines.append(f"来源：{article['source']} | 区域：{article['region']} | 热度分：{article['score']}")
        lines.append(f"发布时间：{article['published_at']} | 入选理由：{article['rationale']}")
        lines.append(f"链接：{article['link']}")
        lines.append("")

    lines.append("## 数据源")
    for url in payload["source_urls"]:
        lines.append(f"- {url}")

    return "\n".join(lines).strip() + "\n"


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_github_summary(payload: dict) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = [
        "## Foreign Market Digest",
        "",
        payload["summary"],
        "",
        "### Top Headlines",
    ]
    for article in payload["articles"][:5]:
        lines.append(f"- {article['title']} ({article['source']})")
    Path(summary_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch foreign market hotspots and generate Chinese copywriting.")
    parser.add_argument("--hours", type=int, default=24, help="Only keep articles published within this many hours.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum number of hotspots to keep.")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON, help="Output path for structured JSON.")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD, help="Output path for generated markdown copy.")
    parser.add_argument("--feishu-webhook", default=os.getenv("FEISHU_WEBHOOK_URL", ""), help="Optional Feishu bot webhook URL.")
    parser.add_argument("--pushplus-token", default=os.getenv("PUSHPLUS_TOKEN", ""), help="Optional PushPlus token for WeChat delivery.")
    parser.add_argument("--wechat-app-id", default=os.getenv("WECHAT_APP_ID", ""), help="Optional WeChat Official Account app id.")
    parser.add_argument("--wechat-app-secret", default=os.getenv("WECHAT_APP_SECRET", ""), help="Optional WeChat Official Account app secret.")
    parser.add_argument("--wechat-author", default=os.getenv("WECHAT_AUTHOR", DEFAULT_WECHAT_AUTHOR), help="WeChat draft author name.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_urls = [feed.get("url") or build_rss_url(feed["query"]) for feed in FEEDS]
    articles = collect_articles(args.hours)[: args.limit]
    if not articles:
        raise RuntimeError("No eligible foreign market articles found in the selected time window.")

    payload = build_payload(articles, args.hours, source_urls)
    write_file(args.output_json, json.dumps(payload, ensure_ascii=False, indent=2))
    write_file(args.output_md, build_markdown(payload))
    write_github_summary(payload)
    if args.pushplus_token:
        push_to_pushplus(payload, args.pushplus_token)
    if args.feishu_webhook:
        push_to_feishu(payload, args.feishu_webhook)
    wechat_media_id = ""
    if args.wechat_app_id and args.wechat_app_secret:
        wechat_media_id = create_wechat_draft(payload, args.wechat_app_id, args.wechat_app_secret, args.wechat_author)

    print(f"Wrote {len(articles)} hotspots to {args.output_json} and {args.output_md}")
    if wechat_media_id:
        print(f"Created WeChat draft with media_id: {wechat_media_id}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
