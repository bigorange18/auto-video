from __future__ import annotations

import io
import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape as html_escape
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

from PIL import Image, ImageOps  # pyright: ignore[reportMissingImports]

from digest_config import (
    DEFAULT_WECHAT_THUMB_CACHE,
    FEEDS,
    HOT_TOPIC_APIS,
    HOT_TOPIC_API_BASE,
    MAJOR_SOURCES,
    FINANCE_IMAGE_HOST_KEYWORDS,
    PUSHPLUS_URL,
    THEMES,
    USER_AGENT,
    WECHAT_ACCESS_TOKEN_URL,
    WECHAT_ADD_DRAFT_URL,
    WECHAT_ADD_MATERIAL_URL,
    WECHAT_COVER_HEIGHT,
    WECHAT_COVER_MIN_HEIGHT,
    WECHAT_COVER_MIN_WIDTH,
    WECHAT_COVER_WIDTH,
)

LOGGER = logging.getLogger("digest")

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


@dataclass
class HotTopic:
    platform: str
    rank: int
    title: str
    hot: str
    url: str
    image: str


class DigestFetcher:
    """Fetches foreign market RSS and domestic hot topics."""

    def build_rss_url(self, query: str) -> str:
        encoded_query = quote(query)
        return f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    def expand_feed_urls(self, feed) -> list[str]:
        urls = [item.strip() for item in feed.urls if item.strip()]
        urls.extend(self.build_rss_url(item.strip()) for item in feed.queries if item.strip())
        deduped: list[str] = []
        seen: set[str] = set()
        for url in urls:
            if url not in seen:
                seen.add(url)
                deduped.append(url)
        return deduped

    def fetch_text(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8")

    def fetch_json(self, url: str) -> dict:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def clean_text(self, value: str | None) -> str:
        if not value:
            return ""
        value = unescape(value)
        value = re.sub(r"<[^>]+>", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def parse_datetime(self, value: str | None) -> datetime | None:
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

    def split_title_and_source(self, raw_title: str, rss_source: str) -> tuple[str, str]:
        if rss_source:
            return raw_title, rss_source
        parts = [part.strip() for part in raw_title.rsplit(" - ", 1)]
        if len(parts) == 2 and 1 < len(parts[1]) <= 40:
            return parts[0], parts[1]
        return raw_title, rss_source or "Unknown"

    def normalize_title(self, title: str) -> str:
        lowered = title.lower()
        lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    def match_theme(self, text: str) -> tuple[str, int]:
        lowered = text.lower()
        best_theme = "市场波动"
        best_hits = 0
        for theme, keywords in THEMES:
            hits = sum(1 for keyword in keywords if keyword in lowered)
            if hits > best_hits:
                best_theme = theme
                best_hits = hits
        return best_theme, best_hits

    def score_article(self, region_weight: int, age_hours: float, hit_count: int, source: str) -> int:
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

    def build_rationale(self, theme: str, age_hours: float, source: str, hit_count: int) -> str:
        reasons: list[str] = [f"主线偏向{theme}"]
        if hit_count >= 2:
            reasons.append("标题触发多个市场关键词")
        if age_hours <= 8:
            reasons.append("发布时间较近")
        if source in MAJOR_SOURCES:
            reasons.append(f"来源为{source}")
        return "，".join(reasons)

    def collect_articles(self, hours: int) -> tuple[list[Article], list[str], list[str]]:
        LOGGER.info("start collecting foreign market articles")
        now = datetime.now(timezone.utc)
        deduped: dict[str, Article] = {}
        failures: list[str] = []
        source_urls: list[str] = []

        for feed in FEEDS:
            candidate_urls = self.expand_feed_urls(feed)
            source_urls.extend(candidate_urls)
            if not candidate_urls:
                failures.append(f"{feed.label}: no feed URL configured")
                continue

            payload = ""
            used_url = ""
            endpoint_errors: list[str] = []
            for url in candidate_urls:
                try:
                    payload = self.fetch_text(url)
                    used_url = url
                    break
                except Exception as exc:  # noqa: BLE001
                    endpoint_errors.append(f"{url} -> {exc}")

            if not payload:
                failures.append(f"{feed.label}: all feed endpoints failed: {' | '.join(endpoint_errors[:2])}")
                continue

            try:
                root = ET.fromstring(payload)
            except ET.ParseError as exc:
                failures.append(f"{feed.label}: invalid RSS payload from {used_url}: {exc}")
                continue

            for item in root.findall("./channel/item"):
                raw_title = self.clean_text(item.findtext("title"))
                if not raw_title:
                    continue
                raw_source = self.clean_text(item.findtext("source") or item.findtext("author"))
                title, source = self.split_title_and_source(raw_title, raw_source)
                published = self.parse_datetime(item.findtext("pubDate"))
                if published is None:
                    continue

                age_hours = (now - published).total_seconds() / 3600
                if age_hours > hours:
                    continue

                link = self.clean_text(item.findtext("link"))
                theme, hit_count = self.match_theme(f"{title} {source}")
                score = self.score_article(feed.weight, age_hours, hit_count, source)
                article = Article(
                    title=title,
                    link=link,
                    source=source,
                    published_at=published.isoformat(),
                    age_hours=round(age_hours, 1),
                    region=feed.label,
                    theme=theme,
                    score=score,
                    rationale=self.build_rationale(theme, age_hours, source, hit_count),
                )
                key = self.normalize_title(title)
                current = deduped.get(key)
                if current is None or article.score > current.score:
                    deduped[key] = article

        articles = sorted(deduped.values(), key=lambda x: (-x.score, x.age_hours, x.title))
        LOGGER.info("collected %d candidate foreign articles", len(articles))
        return articles, failures, source_urls

    def _pick_hot_topic_image(self, item: dict) -> str:
        for key in ("image_url", "pic"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list):
                for part in value:
                    if isinstance(part, str) and part.strip():
                        return part.strip()
        return ""

    def collect_hot_topics(self, limit: int) -> tuple[list[HotTopic], list[str]]:
        LOGGER.info("start collecting domestic hot topics")
        topics: list[HotTopic] = []
        failures: list[str] = []
        for source in HOT_TOPIC_APIS:
            url = f"{HOT_TOPIC_API_BASE}{quote(source.source_type)}"
            try:
                payload = self.fetch_json(url)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{source.name}: {exc}")
                continue

            data = payload.get("data")
            if not isinstance(data, list):
                failures.append(f"{source.name}: invalid payload (missing data list)")
                continue

            for raw in data[:limit]:
                if not isinstance(raw, dict):
                    continue
                title = self.clean_text(str(raw.get("title") or ""))
                if not title:
                    continue
                rank_raw = raw.get("index")
                rank = rank_raw if isinstance(rank_raw, int) else 0
                hot_text = self.clean_text(str(raw.get("hot") or ""))
                topic_url = self.clean_text(str(raw.get("mobilUrl") or raw.get("url") or ""))
                image = self.clean_text(self._pick_hot_topic_image(raw))
                topics.append(HotTopic(source.name, rank, title, hot_text, topic_url, image))
            LOGGER.info("collected %d domestic hot topics", len(topics))
        return topics, failures


class DigestRenderer:
    """Renders summary payload and markdown output."""

    def format_iso_datetime(self, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def build_wechat_article_content(self, payload: dict) -> str:
        parts = [
            f"<h1>{html_escape('海外热点股市日报')}</h1>",
            f"<p><strong>生成时间：</strong>{html_escape(self.format_iso_datetime(str(payload.get('generated_at') or '')))}</p>",
            f"<p><strong>统计窗口：</strong>近 {int(payload.get('window_hours') or 0)} 小时</p>",
            f"<p><strong>一句话概览：</strong>{html_escape(str(payload.get('summary') or ''))}</p>",
        ]

        themes = [str(item).strip() for item in payload.get("themes", []) if str(item).strip()]
        if themes:
            parts.append(f"<p><strong>当前主线：</strong>{html_escape('、'.join(themes))}</p>")

        parts.extend(["<h2>标题建议</h2>", "<ul>"])
        for title in payload.get("headline_candidates", [])[:3]:
            parts.append(f"<li>{html_escape(str(title))}</li>")
        parts.append("</ul>")

        parts.append("<h2>海外热点清单</h2>")
        articles = payload.get("articles", [])
        if articles:
            for index, article in enumerate(articles, start=1):
                title = html_escape(str(article.get("title") or ""))
                region = html_escape(str(article.get("region") or ""))
                theme = html_escape(str(article.get("theme") or ""))
                source = html_escape(str(article.get("source") or ""))
                rationale = html_escape(str(article.get("rationale") or ""))
                published_at = html_escape(self.format_iso_datetime(str(article.get("published_at") or "")))
                score = html_escape(str(article.get("score") or ""))
                link = html_escape(str(article.get("link") or ""))
                parts.append(
                    f"<p><strong>{index}. [{theme}] {title}</strong><br/>"
                    f"区域：{region} | 来源：{source} | 热度分：{score}<br/>"
                    f"发布时间：{published_at}<br/>"
                    f"入选理由：{rationale}<br/>"
                    f"<a href=\"{link}\">查看原文</a></p>"
                )
        else:
            parts.append("<p>当前没有可用的海外热点条目。</p>")

        hot_topics = payload.get("hot_topics", [])
        if hot_topics:
            parts.append("<h2>国内热榜观察</h2>")
            parts.append("<ul>")
            for topic in hot_topics[:12]:
                platform = html_escape(str(topic.get("platform") or ""))
                rank = topic.get("rank")
                rank_text = f"#{rank}" if isinstance(rank, int) and rank > 0 else ""
                title = html_escape(str(topic.get("title") or ""))
                hot = html_escape(str(topic.get("hot") or ""))
                suffix_parts = [part for part in (platform, rank_text, hot) if part]
                suffix = f"（{' | '.join(suffix_parts)}）" if suffix_parts else ""
                parts.append(f"<li>{title}{html_escape(suffix)}</li>")
            parts.append("</ul>")

        short_video_script = str(payload.get("short_video_script") or "").strip()
        if short_video_script:
            parts.extend(["<h2>短视频口播文案</h2>", f"<p>{html_escape(short_video_script)}</p>"])

        social_post = str(payload.get("social_post") or "").strip()
        if social_post:
            parts.extend(["<h2>社媒短文案</h2>", f"<p>{html_escape(social_post)}</p>"])

        fetch_failures = [str(item).strip() for item in payload.get("fetch_failures", []) if str(item).strip()]
        hot_topic_failures = [str(item).strip() for item in payload.get("hot_topic_failures", []) if str(item).strip()]
        if fetch_failures or hot_topic_failures:
            parts.append("<h2>抓取告警</h2>")
            parts.append("<ul>")
            for item in fetch_failures:
                parts.append(f"<li>外盘源异常：{html_escape(item)}</li>")
            for item in hot_topic_failures:
                parts.append(f"<li>热榜源异常：{html_escape(item)}</li>")
            parts.append("</ul>")

        source_urls = [str(item).strip() for item in payload.get("source_urls", []) if str(item).strip()]
        if source_urls:
            parts.append("<h2>数据源</h2>")
            parts.append("<ul>")
            for url in source_urls[:10]:
                escaped_url = html_escape(url)
                parts.append(f"<li><a href=\"{escaped_url}\">{escaped_url}</a></li>")
            if len(source_urls) > 10:
                parts.append(f"<li>其余 {len(source_urls) - 10} 个数据源已省略</li>")
            parts.append("</ul>")

        return "".join(parts)

    def top_themes(self, articles: Iterable[Article], limit: int = 3) -> list[str]:
        counts: dict[str, int] = {}
        for article in articles:
            counts[article.theme] = counts.get(article.theme, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [name for name, _ in ranked[:limit]]

    def build_summary(self, articles: list[Article], hours: int) -> str:
        themes = self.top_themes(articles)
        theme_text = "、".join(themes) if themes else "市场波动"
        return f"先说结论，过去{hours}小时海外市场不是普涨普跌那么简单，真正带节奏的是{theme_text}。"

    def build_headline_candidates(self, themes: list[str]) -> list[str]:
        theme_text = "、".join(themes[:2]) if themes else "海外股市"
        return [
            f"隔夜外盘真正的主线出来了，{theme_text}正在带节奏",
            f"别只看指数涨跌，{theme_text}才是海外市场核心变量",
            "开盘前必须先看这几条，海外资金正在重押这些方向",
        ]

    def build_short_video_script(self, articles: list[Article], hours: int) -> str:
        if not articles:
            return f"过去{hours}小时外盘抓取未成功，当前处于故障诊断模式。"
        themes = self.top_themes(articles)
        return f"先说判断，过去{hours}小时外盘主线集中在{'、'.join(themes)}。"

    def build_social_post(self, articles: list[Article], hours: int) -> str:
        if not articles:
            return f"盘前提示：过去{hours}小时海外市场数据抓取失败，请先排查网络与数据源访问限制。"
        themes = self.top_themes(articles)
        return f"盘前先给结论：过去{hours}小时，海外市场主线是{'、'.join(themes)}。"

    def build_payload(
        self,
        articles: list[Article],
        hot_topics: list[HotTopic],
        source_urls: list[str],
        hours: int,
        failures: list[str],
        hot_topic_failures: list[str],
    ) -> dict:
        themes = self.top_themes(articles)
        summary = self.build_summary(articles, hours)
        if not articles and hot_topics:
            summary = "先说结论，当前内容仅使用国内来源。"
        if not articles and not hot_topics:
            summary = "过去24小时的数据抓取未成功，本次输出为故障诊断模式。"

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "window_hours": hours,
            "source_urls": source_urls,
            "themes": themes,
            "summary": summary,
            "headline_candidates": self.build_headline_candidates(themes),
            "short_video_script": self.build_short_video_script(articles, hours),
            "social_post": self.build_social_post(articles, hours),
            "articles": [asdict(article) for article in articles],
            "fetch_failures": failures,
            "hot_topics": [asdict(topic) for topic in hot_topics],
            "hot_topic_failures": hot_topic_failures,
        }

    def build_markdown(self, payload: dict) -> str:
        lines = [
            "# 海外热点股市信息日报",
            "",
            f"生成时间：{self.format_iso_datetime(payload['generated_at'])}",
            f"统计窗口：近 {payload['window_hours']} 小时",
            "",
            "## 一句话概览",
            payload["summary"],
            "",
            "## 当前主线",
        ]

        if payload["themes"]:
            for theme in payload["themes"]:
                lines.append(f"- {theme}")
        else:
            lines.append("- 市场波动")

        lines.extend([
            "",
            "## 标题建议",
        ])

        for title in payload["headline_candidates"]:
            lines.append(f"- {title}")

        lines.extend(["", "## 短视频口播文案", payload["short_video_script"], "", "## 社媒短文案", payload["social_post"]])
        lines.extend(["", "## 热点清单"])

        for index, article in enumerate(payload["articles"], start=1):
            lines.append(f"{index}. [{article['theme']}] {article['title']}")
            lines.append(f"来源：{article['source']} | 区域：{article['region']} | 热度分：{article['score']}")
            lines.append(f"发布时间：{self.format_iso_datetime(article['published_at'])} | 入选理由：{article['rationale']}")
            lines.append(f"链接：{article['link']}")
            lines.append("")

        if payload["hot_topics"]:
            lines.append("## 国内热榜")
            for topic in payload["hot_topics"]:
                rank = topic.get("rank")
                rank_text = f"#{rank}" if isinstance(rank, int) and rank > 0 else "未标注排名"
                hot = topic.get("hot") or "热度未知"
                lines.append(f"- [{topic['platform']}] {topic['title']} | 排名：{rank_text} | 热度：{hot}")
                if topic.get("url"):
                    lines.append(f"  链接：{topic['url']}")
            lines.append("")

        fetch_failures = payload.get("fetch_failures", [])
        hot_topic_failures = payload.get("hot_topic_failures", [])
        if fetch_failures or hot_topic_failures:
            lines.append("## 抓取告警")
            for item in fetch_failures:
                lines.append(f"- 外盘源异常：{item}")
            for item in hot_topic_failures:
                lines.append(f"- 热榜源异常：{item}")
            lines.append("")

        lines.append("## 数据源")
        for url in payload["source_urls"]:
            lines.append(f"- {url}")

        return "\n".join(lines).strip() + "\n"


class DigestPublisher:
    """Publishes payload to local files and optional external channels."""

    def __init__(self) -> None:
        self.renderer = DigestRenderer()

    def write_file(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def post_json(self, url: str, payload: dict) -> dict:
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
            data = response.read().decode("utf-8")
            if data.strip().startswith("{"):
                return json.loads(data)
            return {"raw": data}

    def create_multipart_body(self, file_bytes: bytes) -> tuple[bytes, str]:
        boundary = f"----AutoVideoBoundary{datetime.now(timezone.utc).timestamp():.0f}"
        body = bytearray()
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(b'Content-Disposition: form-data; name="media"; filename="auto-video-cover.jpg"\r\n')
        body.extend(b"Content-Type: image/jpeg\r\n\r\n")
        body.extend(file_bytes)
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))
        return bytes(body), boundary

    def normalize_wechat_cover_image(self, image_bytes: bytes) -> bytes:
        with Image.open(io.BytesIO(image_bytes)) as image:
            normalized = ImageOps.fit(
                image.convert("RGB"),
                (WECHAT_COVER_WIDTH, WECHAT_COVER_HEIGHT),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            buffer = io.BytesIO()
            normalized.save(buffer, format="JPEG", quality=92, optimize=True)
            return buffer.getvalue()

    def fetch_binary(self, url: str) -> bytes:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=30) as response:
            return response.read()

    def fetch_text(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8", errors="ignore")

    def get_wechat_access_token(self, app_id: str, app_secret: str) -> str:
        url = f"{WECHAT_ACCESS_TOKEN_URL}?grant_type=client_credential&appid={quote(app_id)}&secret={quote(app_secret)}"
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        access_token = payload.get("access_token")
        if access_token:
            return access_token
        raise RuntimeError(f"WeChat access token failed: {payload}")

    def normalize_image_url(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed._replace(query="", fragment="").geturl()

    def load_wechat_thumb_cache(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def save_wechat_thumb_cache(self, path: Path, cache: dict) -> None:
        self.write_file(path, json.dumps(cache, ensure_ascii=False, indent=2))

    def extract_meta_image_urls(self, page_url: str, html: str) -> list[str]:
        patterns = (
            r'<meta[^>]+(?:property|name)=["\'](?:og:image|og:image:url|twitter:image)["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|og:image:url|twitter:image)["\']',
        )
        candidates: list[str] = []
        for pattern in patterns:
            for item in re.findall(pattern, html, flags=re.IGNORECASE):
                image_url = item.strip()
                if not image_url:
                    continue
                candidates.append(urljoin(page_url, image_url))

        deduped: list[str] = []
        seen: set[str] = set()
        for url in candidates:
            normalized = self.normalize_image_url(url)
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(url)
        return deduped

    def collect_cover_candidates(self, payload: dict) -> list[dict[str, str]]:
        candidates: list[dict[str, str]] = []

        for article in payload.get("articles", [])[:6]:
            article_url = (article.get("link") or "").strip()
            if not article_url:
                continue
            try:
                html = self.fetch_text(article_url)
            except Exception as exc:  # noqa: BLE001
                LOGGER.info("skip article cover extraction from %s: %s", article_url, exc)
                continue

            image_urls = self.extract_meta_image_urls(article_url, html)
            for image_url in image_urls[:3]:
                candidates.append(
                    {
                        "url": image_url,
                        "kind": "finance",
                        "source": str(article.get("source") or ""),
                        "title": str(article.get("title") or ""),
                        "theme": str(article.get("theme") or ""),
                    }
                )

        for topic in payload.get("hot_topics", []):
            image_url = (topic.get("image") or "").strip()
            if not image_url:
                continue
            candidates.append(
                {
                    "url": image_url,
                    "kind": "hot_topic",
                    "source": str(topic.get("platform") or ""),
                    "title": str(topic.get("title") or ""),
                    "theme": "",
                }
            )

        deduped: list[dict[str, str]] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = self.normalize_image_url(candidate["url"])
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(candidate)
        LOGGER.info("collected %d cover candidates", len(deduped))
        return deduped

    def get_dominant_themes(self, payload: dict, limit: int = 2) -> list[str]:
        counts: dict[str, int] = {}
        for article in payload.get("articles", []):
            theme = str(article.get("theme") or "").strip()
            if not theme:
                continue
            counts[theme] = counts.get(theme, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [name for name, _ in ranked[:limit]]

    def score_theme_consistency(self, candidate: dict[str, str], dominant_themes: list[str]) -> int:
        if not dominant_themes:
            return 0

        candidate_theme = (candidate.get("theme") or "").strip()
        source = (candidate.get("source") or "").lower()
        title = (candidate.get("title") or "").lower()
        url = (candidate.get("url") or "").lower()
        text = f"{source} {title} {url}"
        score = 0

        if candidate_theme and candidate_theme in dominant_themes:
            score += 8

        theme_keyword_map = {name: keywords for name, keywords in THEMES}
        for theme in dominant_themes:
            keywords = theme_keyword_map.get(theme, ())
            hits = sum(1 for keyword in keywords if keyword in text)
            score += hits * 2

        if candidate.get("kind") == "finance" and score > 0:
            score += 2
        return score

    def evaluate_cover_candidate(
        self,
        candidate: dict[str, str],
        dominant_themes: list[str],
    ) -> tuple[int, bytes] | None:
        image_url = candidate["url"]
        try:
            image_bytes = self.fetch_binary(image_url)
            with Image.open(io.BytesIO(image_bytes)) as image:
                width, height = image.size
        except Exception as exc:  # noqa: BLE001
            LOGGER.info("cover candidate unreadable: %s (%s)", image_url, exc)
            return None

        if width < WECHAT_COVER_MIN_WIDTH or height < WECHAT_COVER_MIN_HEIGHT:
            LOGGER.info("cover candidate rejected (too small): %s (%dx%d)", image_url, width, height)
            return None

        ratio = width / max(height, 1)
        if ratio < 1.1 or ratio > 2.8:
            LOGGER.info("cover candidate rejected (bad ratio): %s (%.2f)", image_url, ratio)
            return None

        consistency_score = self.score_theme_consistency(candidate, dominant_themes)
        if dominant_themes and consistency_score <= 0 and candidate.get("kind") != "finance":
            LOGGER.info(
                "cover candidate rejected (theme mismatch): %s themes=%s",
                image_url,
                ",".join(dominant_themes),
            )
            return None

        parsed = urlparse(image_url)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        score = 0

        if candidate.get("kind") == "finance":
            score += 8
        if any(keyword in host for keyword in FINANCE_IMAGE_HOST_KEYWORDS):
            score += 6
        if any(token in path for token in ("logo", "icon", "avatar", "sprite")):
            score -= 8

        source_text = (candidate.get("source") or "").lower()
        title_text = (candidate.get("title") or "").lower()
        if source_text and any(word in host for word in source_text.split() if len(word) > 3):
            score += 2
        if title_text and any(word in path for word in title_text.split()[:4] if len(word) > 4):
            score += 1

        score += consistency_score

        LOGGER.info(
            "cover candidate score=%d consistency=%d host=%s url=%s",
            score,
            consistency_score,
            host,
            image_url,
        )
        return score, image_bytes

    def upload_wechat_image_bytes(self, access_token: str, image_bytes: bytes) -> str:
        normalized_bytes = self.normalize_wechat_cover_image(image_bytes)
        upload_url = f"{WECHAT_ADD_MATERIAL_URL}?access_token={quote(access_token)}&type=image"
        body, boundary = self.create_multipart_body(normalized_bytes)
        request = Request(
            upload_url,
            data=body,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        media_id = result.get("media_id")
        if media_id:
            return media_id
        raise RuntimeError(f"WeChat image upload failed: {result}")

    def resolve_wechat_thumb_media_id(
        self,
        payload: dict,
        access_token: str,
        preferred_media_id: str,
        use_cache: bool = True,
    ) -> str:
        if preferred_media_id:
            return preferred_media_id

        cache = self.load_wechat_thumb_cache(DEFAULT_WECHAT_THUMB_CACHE)
        candidates = self.collect_cover_candidates(payload)
        dominant_themes = self.get_dominant_themes(payload)
        if dominant_themes:
            LOGGER.info("cover dominant themes: %s", ",".join(dominant_themes))
        evaluated: list[tuple[int, dict[str, str], bytes]] = []
        fallback_cached_media_id = ""

        for candidate in candidates:
            image_url = (candidate.get("url") or "").strip()
            if not image_url:
                continue

            cache_key = self.normalize_image_url(image_url)
            cached_media_id = cache.get(cache_key) if use_cache else ""
            if cached_media_id:
                if candidate.get("kind") == "finance":
                    LOGGER.info("wechat cover hit finance cache: %s", cache_key)
                    return cached_media_id
                if not fallback_cached_media_id:
                    LOGGER.info("wechat cover hit fallback cache: %s", cache_key)
                    fallback_cached_media_id = cached_media_id
                continue

            evaluation = self.evaluate_cover_candidate(candidate, dominant_themes)
            if evaluation is None:
                continue
            score, image_bytes = evaluation
            evaluated.append((score, candidate, image_bytes))

        evaluated.sort(key=lambda item: item[0], reverse=True)

        for score, candidate, image_bytes in evaluated:
            image_url = candidate["url"]
            cache_key = self.normalize_image_url(image_url)
            try:
                media_id = self.upload_wechat_image_bytes(access_token, image_bytes)
            except Exception as exc:  # noqa: BLE001
                LOGGER.info("cover upload failed for %s: %s", image_url, exc)
                continue
            cache[cache_key] = media_id
            self.save_wechat_thumb_cache(DEFAULT_WECHAT_THUMB_CACHE, cache)
            LOGGER.info(
                "selected wechat cover score=%d kind=%s source=%s url=%s",
                score,
                candidate.get("kind", ""),
                candidate.get("source", ""),
                image_url,
            )
            return media_id

        if fallback_cached_media_id:
            return fallback_cached_media_id

        raise RuntimeError("unable to derive WECHAT_THUMB_MEDIA_ID from hot topic images")

    def create_wechat_draft(self, payload: dict, app_id: str, app_secret: str, author: str, thumb_media_id: str) -> str:
        access_token = self.get_wechat_access_token(app_id, app_secret)
        url = f"{WECHAT_ADD_DRAFT_URL}?access_token={quote(access_token)}"

        def _submit(resolved_media_id: str) -> dict:
            draft_payload = {
                "articles": [
                    {
                        "title": "海外热点股市日报",
                        "author": author,
                        "digest": payload["summary"],
                        "content": self.renderer.build_wechat_article_content(payload),
                        "content_source_url": "",
                        "thumb_media_id": resolved_media_id,
                        "need_open_comment": 0,
                        "only_fans_can_comment": 0,
                    }
                ]
            }
            return self.post_json(url, draft_payload)

        resolved_thumb_media_id = self.resolve_wechat_thumb_media_id(
            payload,
            access_token,
            thumb_media_id,
            use_cache=True,
        )
        response = _submit(resolved_thumb_media_id)
        media_id = response.get("media_id")
        if media_id:
            return media_id

        text = str(response)
        if "errcode" in text and "40007" in text and not thumb_media_id:
            LOGGER.info("wechat media_id invalid, retrying with fresh uploaded cover")
            resolved_thumb_media_id = self.resolve_wechat_thumb_media_id(
                payload,
                access_token,
                thumb_media_id,
                use_cache=False,
            )
            response = _submit(resolved_thumb_media_id)
            media_id = response.get("media_id")
            if media_id:
                return media_id

        raise RuntimeError(f"WeChat draft creation failed: {response}")


class ForeignMarketDigestService:
    """Orchestrates fetch, render and publish workflow."""

    def __init__(self, args) -> None:
        self.args = args
        self.fetcher = DigestFetcher()
        self.renderer = DigestRenderer()
        self.publisher = DigestPublisher()

    def run(self) -> int:
        LOGGER.info("digest run started")
        articles, failures, source_urls = self.fetcher.collect_articles(self.args.hours)
        articles = articles[: self.args.limit]
        hot_topics, hot_topic_failures = self.fetcher.collect_hot_topics(self.args.hot_limit)

        if not articles and self.args.strict_fetch:
            reason = " | ".join(failures) if failures else "No eligible foreign market articles found."
            raise RuntimeError(reason)

        payload = self.renderer.build_payload(
            articles=articles,
            hot_topics=hot_topics,
            source_urls=source_urls,
            hours=self.args.hours,
            failures=failures,
            hot_topic_failures=hot_topic_failures,
        )

        self.publisher.write_file(
            self.args.output_json,
            json.dumps(payload, ensure_ascii=False, indent=2),
        )
        self.publisher.write_file(self.args.output_md, self.renderer.build_markdown(payload))

        if self.args.pushplus_token:
            try:
                self.publisher.post_json(
                    PUSHPLUS_URL,
                    {
                        "token": self.args.pushplus_token,
                        "title": "海外热点股市日报",
                        "content": self.renderer.build_markdown(payload),
                        "template": "markdown",
                    },
                )
                LOGGER.info("pushplus push completed")
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("PushPlus push skipped: %s", exc)

        wechat_media_id = ""
        if self.args.wechat_app_id and self.args.wechat_app_secret:
            try:
                wechat_media_id = self.publisher.create_wechat_draft(
                    payload,
                    self.args.wechat_app_id,
                    self.args.wechat_app_secret,
                    self.args.wechat_author,
                    self.args.wechat_thumb_media_id,
                )
                LOGGER.info("wechat draft created")
            except Exception as exc:  # noqa: BLE001
                if self.args.strict_wechat:
                    raise
                LOGGER.warning("WeChat draft skipped: %s", exc)

        LOGGER.info(
            "[KEY] Wrote %d hotspots to %s and %s",
            len(articles),
            self.args.output_json,
            self.args.output_md,
        )
        if failures:
            LOGGER.warning("Fetch warnings:")
            for item in failures:
                LOGGER.warning("- %s", item)
        if hot_topic_failures:
            LOGGER.warning("Hot topic fetch warnings:")
            for item in hot_topic_failures:
                LOGGER.warning("- %s", item)
        if wechat_media_id:
            LOGGER.info("[KEY] Created WeChat draft with media_id: %s", wechat_media_id)

        LOGGER.info("digest run finished with %d articles", len(articles))
        return 0
