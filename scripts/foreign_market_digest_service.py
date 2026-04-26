from __future__ import annotations

import io
import json
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape as html_escape
from html import unescape
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urljoin, urlparse
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont, ImageOps  # pyright: ignore[reportMissingImports]

from digest_config import (
    BAIDU_HOT_API_TYPE,
    DEFAULT_LLM_ARTICLE_SCORING_PROMPT_MD,
    DEFAULT_LLM_COPYWRITING_PROMPT_MD,
    DEFAULT_WECHAT_THUMB_CACHE,
    DOMESTIC_RSS_SOURCES,
    FEEDS,
    HOT_TOPIC_API_BASE,
    MAGNIFICENT_SEVEN_MAP,
    MAJOR_SOURCES,
    FINANCE_IMAGE_HOST_KEYWORDS,
    PUSHPLUS_URL,
    THEMES,
    USER_AGENT,
    WSCN_LIVES_API_URL,
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
    summary: str
    image: str
    focus_companies: str
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
    summary: str
    hot: str
    url: str
    image: str


class DigestFetcher:
    """Fetches foreign market RSS and domestic hot topics."""

    HOT_TOPIC_SUMMARY_ENRICH_LIMIT = int(os.getenv("HOT_TOPIC_SUMMARY_ENRICH_LIMIT", "12") or "12")
    MAGNIFICENT_SEVEN_ONLY = os.getenv("MAGNIFICENT_SEVEN_ONLY", "1") != "0"
    FEED_REQUEST_TIMEOUT = int(os.getenv("FEED_REQUEST_TIMEOUT", "12") or "12")
    FEED_RETRY_TIMEOUT = int(os.getenv("FEED_RETRY_TIMEOUT", "15") or "15")

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
        try:
            with urlopen(request, timeout=self.FEED_REQUEST_TIMEOUT) as response:
                return response.read().decode("utf-8")
        except Exception:
            if "nasdaq.com" not in url:
                raise
            # Nasdaq RSS can intermittently reject non-browser signatures or respond slowly.
            retry_request = Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                },
            )
            with urlopen(retry_request, timeout=self.FEED_RETRY_TIMEOUT) as response:
                return response.read().decode("utf-8")

    def fetch_json(self, url: str) -> dict:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch_web_text(self, url: str, timeout: int = 12) -> str:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            content_type = response.headers.get("Content-Type", "")

        charset = ""
        match = re.search(r"charset=([a-zA-Z0-9_\-]+)", content_type, flags=re.IGNORECASE)
        if match:
            charset = match.group(1).strip()

        encodings = [charset, "utf-8", "gb18030", "gbk", "latin-1"]
        seen: set[str] = set()
        for encoding in encodings:
            if not encoding or encoding in seen:
                continue
            seen.add(encoding)
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="ignore")

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
            hits = 0
            for keyword in keywords:
                key = keyword.lower()
                if re.fullmatch(r"[a-z0-9\-\s\.\+]+", key):
                    if re.search(rf"\b{re.escape(key)}\b", lowered):
                        hits += 1
                else:
                    if key in lowered:
                        hits += 1
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

    def find_magnificent_seven_companies(self, text: str) -> list[str]:
        lowered = text.lower()
        matched: list[str] = []
        for company, aliases in MAGNIFICENT_SEVEN_MAP.items():
            if any(alias in lowered for alias in aliases):
                matched.append(company)
        return matched

    def build_rationale(self, theme: str, age_hours: float, source: str, hit_count: int) -> str:
        reasons: list[str] = [f"主线偏向{theme}"]
        if hit_count >= 2:
            reasons.append("标题触发多个市场关键词")
        if age_hours <= 8:
            reasons.append("发布时间较近")
        if source in MAJOR_SOURCES:
            reasons.append(f"来源为{source}")
        return "，".join(reasons)

    def _extract_image_from_html(self, html: str) -> str:
        if not html:
            return ""
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
        if not match:
            return ""
        return self.clean_text(match.group(1))

    def _extract_article_image(self, item: ET.Element, raw_description: str) -> str:
        enclosure = item.find("enclosure")
        if enclosure is not None:
            url = self.clean_text(enclosure.attrib.get("url", ""))
            if url:
                return url

        namespaces = {"media": "http://search.yahoo.com/mrss/"}
        for tag in ("media:content", "media:thumbnail"):
            node = item.find(tag, namespaces)
            if node is None:
                continue
            url = self.clean_text(node.attrib.get("url", ""))
            if url:
                return url

        return self._extract_image_from_html(raw_description)

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
            endpoint_errors: list[str] = []
            success_count = 0
            for url in candidate_urls:
                try:
                    payload = self.fetch_text(url)
                except Exception as exc:  # noqa: BLE001
                    endpoint_errors.append(f"{url} -> {exc}")
                    continue

                try:
                    root = ET.fromstring(payload)
                except ET.ParseError as exc:
                    endpoint_errors.append(f"{url} -> invalid RSS payload: {exc}")
                    continue

                success_count += 1

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
                    raw_description = item.findtext("description") or ""
                    summary = self.clean_text(raw_description or item.findtext("summary"))
                    image = self._extract_article_image(item, raw_description)
                    matched_companies = self.find_magnificent_seven_companies(f"{title} {summary} {source}")
                    if self.MAGNIFICENT_SEVEN_ONLY and not matched_companies:
                        continue
                    theme, hit_count = self.match_theme(f"{title} {summary} {source}")
                    score = self.score_article(feed.weight, age_hours, hit_count, source)
                    if matched_companies:
                        score += len(matched_companies) * 8
                    focus_companies = "、".join(matched_companies)
                    rationale = self.build_rationale(theme, age_hours, source, hit_count)
                    if matched_companies:
                        rationale = f"{rationale}，涉及七巨头：{focus_companies}"
                    article = Article(
                        title=title,
                        summary=summary,
                        image=image,
                        focus_companies=focus_companies,
                        link=link,
                        source=source,
                        published_at=published.isoformat(),
                        age_hours=round(age_hours, 1),
                        region=feed.label,
                        theme=theme,
                        score=score,
                        rationale=rationale,
                    )
                    key = self.normalize_title(title)
                    current = deduped.get(key)
                    if current is None or article.score > current.score:
                        deduped[key] = article

            if success_count == 0:
                failures.append(f"{feed.label}: all feed endpoints failed: {' | '.join(endpoint_errors[:2])}")

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

    def _extract_meta_descriptions(self, html: str) -> list[str]:
        patterns = (
            r'<meta[^>]+(?:property|name)=["\'](?:description|og:description|twitter:description)["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:description|og:description|twitter:description)["\']',
        )
        result: list[str] = []
        for pattern in patterns:
            for item in re.findall(pattern, html, flags=re.IGNORECASE):
                text = self.clean_text(item)
                if text:
                    result.append(text)
        return result

    def _extract_paragraph_candidates(self, html: str) -> list[str]:
        matches = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.IGNORECASE | re.DOTALL)
        candidates: list[str] = []
        for raw in matches[:80]:
            text = self.clean_text(raw)
            if len(text) >= 24:
                candidates.append(text)
        return candidates

    def _extract_script_candidates(self, html: str) -> list[str]:
        candidates: list[str] = []
        # JSON-like fields often appear in SSR/data scripts for article pages.
        patterns = (
            r'"(?:description|abstract|summary|sub_title|content|articleBody)"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"',
            r"'(?:description|abstract|summary|sub_title|content|articleBody)'\s*:\s*'([^'\\]*(?:\\.[^'\\]*)*)'",
        )
        for pattern in patterns:
            for raw in re.findall(pattern, html, flags=re.IGNORECASE):
                text = raw.encode("utf-8").decode("unicode_escape", errors="ignore")
                text = self.clean_text(text)
                if len(text) >= 24:
                    candidates.append(text)
        return candidates

    def _extract_text_block_candidates(self, html: str) -> list[str]:
        text = self.clean_text(re.sub(r"<[^>]+>", " ", html))
        if not text:
            return []
        chunks = re.split(r"[。!?！？]\s*", text)
        candidates: list[str] = []
        for chunk in chunks:
            cleaned = self.clean_text(chunk)
            if len(cleaned) >= 32:
                candidates.append(cleaned)
            if len(candidates) >= 20:
                break
        return candidates

    def _select_best_summary(self, title: str, candidates: list[str]) -> str:
        normalized_title = self.clean_text(title).lower()
        for candidate in candidates:
            cleaned = self.clean_text(candidate)
            if not cleaned:
                continue
            if cleaned.lower() == normalized_title:
                continue
            if len(cleaned) < 20:
                continue
            lowered = cleaned.lower()
            if re.search(r"\b(function|window|document|var|const|let|return|webpack|script|undefined)\b", lowered):
                continue
            if cleaned.count("{") + cleaned.count("}") + cleaned.count("=") >= 3:
                continue
            if len(re.findall(r"[\u4e00-\u9fff]", cleaned)) < 6:
                continue
            return cleaned
        return ""

    def extract_hot_topic_summary_from_url(self, topic_url: str, title: str) -> str:
        html = self.fetch_web_text(topic_url, timeout=10)
        candidates: list[str] = []
        candidates.extend(self._extract_meta_descriptions(html))
        candidates.extend(self._extract_paragraph_candidates(html))
        candidates.extend(self._extract_script_candidates(html))
        candidates.extend(self._extract_text_block_candidates(html))
        return self._select_best_summary(title, candidates)

    def collect_hot_topics(self, limit: int) -> tuple[list[HotTopic], list[str]]:
        LOGGER.info("start collecting domestic hot topics")
        topics: list[HotTopic] = []
        failures: list[str] = []

        topics.extend(self._collect_hot_topics_from_rss(limit, failures))
        topics.extend(self._collect_hot_topics_from_wscn(limit, failures))
        topics.extend(self._collect_hot_topics_from_baidu(limit, failures))

        LOGGER.info("collected %d domestic hot topics", len(topics))
        return topics, failures

    def _collect_hot_topics_from_rss(self, limit: int, failures: list[str]) -> list[HotTopic]:
        topics: list[HotTopic] = []
        for source in DOMESTIC_RSS_SOURCES:
            try:
                payload = self.fetch_text(source.url)
                root = ET.fromstring(payload)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{source.name}: {exc}")
                continue

            items = root.findall("./channel/item")
            if not items:
                items = root.findall(".//item")

            for index, item in enumerate(items[:limit], start=1):
                title = self.clean_text(item.findtext("title"))
                if not title:
                    continue
                summary = self.clean_text(
                    item.findtext("description")
                    or item.findtext("summary")
                    or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
                )
                topic_url = self.clean_text(item.findtext("link") or item.findtext("guid"))
                topics.append(HotTopic(source.name, index, title, summary, "", topic_url, ""))
        return topics

    def _collect_hot_topics_from_wscn(self, limit: int, failures: list[str]) -> list[HotTopic]:
        topics: list[HotTopic] = []
        try:
            payload = self.fetch_json(WSCN_LIVES_API_URL)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"华尔街见闻快讯: {exc}")
            return topics

        data = payload.get("data") if isinstance(payload, dict) else None
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            failures.append("华尔街见闻快讯: invalid payload (missing data.items list)")
            return topics

        for index, raw in enumerate(items[:limit], start=1):
            if not isinstance(raw, dict):
                continue
            title = self.clean_text(str(raw.get("title") or ""))
            if not title:
                continue
            summary = self.clean_text(
                str(raw.get("content_text") or raw.get("content") or raw.get("description") or "")
            )
            topic_url = self.clean_text(str(raw.get("uri") or raw.get("url") or raw.get("share_uri") or ""))
            if topic_url.startswith("/"):
                topic_url = urljoin("https://wallstreetcn.com", topic_url)
            hot_text = self.clean_text(str(raw.get("importance") or ""))
            topics.append(HotTopic("华尔街见闻快讯", index, title, summary, hot_text, topic_url, ""))
        return topics

    def _collect_hot_topics_from_baidu(self, limit: int, failures: list[str]) -> list[HotTopic]:
        topics: list[HotTopic] = []
        url = f"{HOT_TOPIC_API_BASE}{quote(BAIDU_HOT_API_TYPE)}"
        try:
            payload = self.fetch_json(url)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"百度热搜: {exc}")
            return topics

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            failures.append("百度热搜: invalid payload (missing data list)")
            return topics

        for index, raw in enumerate(data[:limit], start=1):
            if not isinstance(raw, dict):
                continue
            title = self.clean_text(str(raw.get("title") or ""))
            if not title:
                continue
            rank_raw = raw.get("index")
            rank = rank_raw if isinstance(rank_raw, int) and rank_raw > 0 else index
            summary = self.clean_text(str(raw.get("desc") or raw.get("summary") or raw.get("content") or ""))
            hot_text = self.clean_text(str(raw.get("hot") or ""))
            topic_url = self.clean_text(str(raw.get("mobilUrl") or raw.get("url") or ""))
            image = self.clean_text(self._pick_hot_topic_image(raw))
            topics.append(HotTopic("百度热搜", rank, title, summary, hot_text, topic_url, image))
        return topics


class DigestRenderer:
    """Renders summary payload and markdown output."""

    def clean_text(self, value: str | None) -> str:
        if not value:
            return ""
        value = unescape(value)
        value = re.sub(r"<[^>]+>", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def format_iso_datetime(self, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def normalize_topic_title(self, title: str) -> str:
        lowered = title.lower().strip()
        return re.sub(r"[^\w\u4e00-\u9fff]+", "", lowered)

    def parse_hot_value(self, hot: str) -> float:
        match = re.search(r"(\d+(?:\.\d+)?)", hot)
        if not match:
            return 0.0
        value = float(match.group(1))
        if "亿" in hot:
            value *= 100000000
        elif "万" in hot:
            value *= 10000
        return value

    def select_key_hot_topics(self, hot_topics: list[HotTopic] | list[dict], limit: int = 8) -> list[dict[str, Any]]:
        deduped: dict[str, dict[str, Any]] = {}
        for raw in hot_topics:
            topic = raw if isinstance(raw, dict) else asdict(raw)
            title = str(topic.get("title") or "").strip()
            if not title:
                continue
            key = self.normalize_topic_title(title)
            rank = topic.get("rank")
            rank_value = rank if isinstance(rank, int) and rank > 0 else 9999
            hot_value = self.parse_hot_value(str(topic.get("hot") or ""))
            current = deduped.get(key)
            if current is None:
                deduped[key] = dict(topic)
                continue
            current_rank = current.get("rank") if isinstance(current.get("rank"), int) else 9999
            current_hot_value = self.parse_hot_value(str(current.get("hot") or ""))
            if rank_value < current_rank or (rank_value == current_rank and hot_value > current_hot_value):
                deduped[key] = dict(topic)

        ranked = sorted(
            deduped.values(),
            key=lambda item: (
                item.get("rank") if isinstance(item.get("rank"), int) and item.get("rank") > 0 else 9999,
                -self.parse_hot_value(str(item.get("hot") or "")),
                str(item.get("platform") or ""),
                str(item.get("title") or ""),
            ),
        )
        return ranked[:limit]

    def classify_hot_topic(self, title: str) -> str:
        categories = (
            ("宏观政策", ("总书记", "习近平", "贺电", "国债", "政策", "经济", "战略", "两岸", "外交")),
            ("国际局势", ("美国", "伊朗", "中东", "外国", "台湾", "军舰", "非洲")),
            ("消费金融", ("消费", "花呗", "白条", "月付", "车展", "抢货", "市场")),
            ("科技产业", ("ai", "航天", "月球", "芯片", "科技", "机器人")),
            ("体育文娱", ("苏超", "中超", "vs", "日落", "看哭", "全网")),
            ("社会民生", ("病情", "游客", "健康", "回家", "被罚", "谣言", "楼房")),
        )
        lowered = title.lower()
        for category, keywords in categories:
            if any(keyword.lower() in lowered for keyword in keywords):
                return category
        return "公共舆情"

    def compress_source_text(self, title: str, summary: str, max_length: int = 120) -> str:
        title = self.clean_text(title)
        summary = self.clean_text(summary)
        if summary:
            combined = f"{title}。{summary}"
        else:
            combined = title
        combined = re.sub(r"\s+", " ", combined).strip(" 。；;，,")
        if len(combined) <= max_length:
            return combined
        clipped = combined[: max_length - 1].rstrip(" ，。；;,:：")
        return f"{clipped}…"

    def build_article_analysis(self, article: dict[str, Any]) -> str:
        return self.compress_source_text(
            str(article.get("title") or ""),
            str(article.get("summary") or ""),
            max_length=140,
        )

    def build_article_brief(self, article: dict[str, Any]) -> str:
        """Return a concise foreign-hotspot brief with lightweight details."""
        summary = self.clean_text(str(article.get("summary") or ""))
        if not summary:
            summary = self.clean_text(str(article.get("title") or ""))
        summary = re.sub(r"\s+", " ", summary).strip(" 。；;，,")

        meta_parts: list[str] = []
        source = str(article.get("source") or "").strip()
        region = str(article.get("region") or "").strip()
        focus_companies = str(article.get("focus_companies") or "").strip()
        published = self.format_iso_datetime(str(article.get("published_at") or ""))

        if published:
            meta_parts.append(f"时间{published}")
        if focus_companies:
            meta_parts.append(f"七巨头{focus_companies}")
        if source:
            meta_parts.append(f"来源{source}")
        if region:
            meta_parts.append(f"区域{region}")

        details = "；".join(meta_parts)
        if details:
            details_budget = len(details) + 1
            summary_budget = max(40, 200 - details_budget)
            summary_text = self.compress_source_text("", summary, max_length=summary_budget)
            combined = f"{summary_text}。{details}"
        else:
            combined = self.compress_source_text("", summary, max_length=200)

        if len(combined) > 200:
            combined = self.compress_source_text("", combined, max_length=200)
        return self.compress_source_text("", combined, max_length=200)

    def build_hot_topic_analysis(self, topic: dict[str, Any]) -> str:
        title = self.clean_text(str(topic.get("title") or ""))
        summary = self.clean_text(str(topic.get("summary") or ""))
        if summary and summary != title:
            return summary
        return title

    def build_summary(self, articles: list[Article], hot_topics: list[HotTopic], hours: int) -> str:
        foreign_themes = self.top_themes(articles)
        domestic_topics = self.select_key_hot_topics(hot_topics, limit=3)
        foreign_text = "、".join(foreign_themes) if foreign_themes else "海外市场波动"
        domestic_text = "、".join(str(item.get("title") or "") for item in domestic_topics if str(item.get("title") or ""))
        if articles and domestic_topics:
            return (
                f"过去{hours}小时，海外热点主要集中在{foreign_text}，国内舆论场则围绕{domestic_text}等话题升温。"
                "这份内容会先做总览，再分别拆解国内外热点的核心信息与后续观察点。"
            )
        if articles:
            return f"过去{hours}小时，内容重点集中在海外市场的{foreign_text}，下文将逐条拆解每个热点的影响线索。"
        if domestic_topics:
            return f"过去{hours}小时，当前可用内容主要来自国内热榜，热点集中在{domestic_text}，下文按条目展开分析。"
        return f"过去{hours}小时的数据抓取未成功，本次输出为故障诊断模式。"

    def build_title(self, themes: list[str], hot_topics: list[HotTopic]) -> str:
        foreign_text = themes[0] if themes else "海外市场"
        key_hot_topics = self.select_key_hot_topics(hot_topics, limit=3)
        domestic_titles = [str(item.get("title") or "").strip() for item in key_hot_topics if str(item.get("title") or "").strip()]
        domestic_title = domestic_titles[0] if domestic_titles else "国内热榜"

        if themes and domestic_titles:
            return f"国内外热点观察：{foreign_text}升温，{domestic_title}受关注"
        if themes:
            return f"海外热点观察：{foreign_text}，哪些信号最值得跟踪"
        if domestic_titles:
            return f"国内热点观察：{domestic_title}，哪些变化值得继续跟踪"
        return "国内外热点总结分析"

    def build_short_video_script(self, articles: list[Article], hot_topics: list[HotTopic], hours: int) -> str:
        if not articles and not hot_topics:
            return f"过去{hours}小时数据抓取未成功，当前内容以故障诊断为主。"
        foreign_text = "、".join(self.top_themes(articles)[:3]) if articles else "海外暂无有效样本"
        domestic_titles = [str(item.get("title") or "") for item in self.select_key_hot_topics(hot_topics, limit=2)]
        domestic_text = "、".join(domestic_titles) if domestic_titles else "国内热榜暂无重点样本"
        return (
            f"先看总览，过去{hours}小时海外热点集中在{foreign_text}，"
            f"国内热榜里更值得跟踪的是{domestic_text}。下面不只做汇总，还会逐条看每个热点背后的信号。"
        )

    def build_social_post(self, articles: list[Article], hot_topics: list[HotTopic], hours: int) -> str:
        if not articles and not hot_topics:
            return f"过去{hours}小时数据抓取失败，建议先排查网络、源站可达性和接口限制。"
        foreign_text = "、".join(self.top_themes(articles)[:2]) if articles else "海外市场"
        domestic_titles = [str(item.get("title") or "") for item in self.select_key_hot_topics(hot_topics, limit=1)]
        domestic_text = domestic_titles[0] if domestic_titles else "国内热榜"
        return f"今天这版内容把海外的{foreign_text}和国内的{domestic_text}放到一起看，不只列热点，也补上每条热点的分析角度。"

    def build_wechat_article_content(self, payload: dict) -> str:
        key_hot_topics = self.select_key_hot_topics(payload.get("hot_topics", []), limit=8)
        parts = [
            f"<h1>{html_escape(str(payload.get('title') or '国内外热点总结分析'))}</h1>",
            f"<p><strong>生成时间：</strong>{html_escape(self.format_iso_datetime(str(payload.get('generated_at') or '')))}</p>",
            f"<p><strong>统计窗口：</strong>近 {int(payload.get('window_hours') or 0)} 小时</p>",
            f"<p><strong>一句话概览：</strong>{html_escape(str(payload.get('summary') or ''))}</p>",
        ]

        themes = [str(item).strip() for item in payload.get("themes", []) if str(item).strip()]
        if themes:
            parts.append(f"<p><strong>当前主线：</strong>{html_escape('、'.join(themes))}</p>")

        parts.append("<h2>海外热点简讯</h2>")
        articles = payload.get("articles", [])
        if articles:
            for index, article in enumerate(articles, start=1):
                title = html_escape(str(article.get("title") or ""))
                theme = html_escape(str(article.get("theme") or ""))
                link = html_escape(str(article.get("link") or ""))
                brief = html_escape(self.build_article_brief(article))
                image_url = html_escape(str(article.get("image") or ""))
                image_html = (
                    f"<img src=\"{image_url}\" alt=\"{title}\" style=\"width:100%;max-width:720px;border-radius:8px;\"/><br/>"
                    if image_url
                    else ""
                )
                parts.append(
                    f"<p><strong>{index}. [{theme}] {title}</strong><br/>"
                    f"{image_html}"
                    f"内容：{brief}<br/>"
                    f"<a href=\"{link}\">查看原文</a></p>"
                )
        else:
            parts.append("<p>当前没有可用的海外热点条目。</p>")

        if key_hot_topics:
            parts.append("<h2>国内热点分析</h2>")
            for index, topic in enumerate(key_hot_topics, start=1):
                platform = html_escape(str(topic.get("platform") or ""))
                rank = topic.get("rank")
                rank_text = f"#{rank}" if isinstance(rank, int) and rank > 0 else ""
                title = html_escape(str(topic.get("title") or ""))
                hot = html_escape(str(topic.get("hot") or ""))
                suffix_parts = [part for part in (platform, rank_text, hot) if part]
                suffix = f"（{' | '.join(suffix_parts)}）" if suffix_parts else ""
                url = html_escape(str(topic.get("url") or ""))
                content = html_escape(self.build_hot_topic_analysis(topic))
                image_url = html_escape(str(topic.get("image") or ""))
                image_html = (
                    f"<img src=\"{image_url}\" alt=\"{title}\" style=\"width:100%;max-width:720px;border-radius:8px;\"/><br/>"
                    if image_url
                    else ""
                )
                link_html = f"<a href=\"{url}\">查看热榜</a>" if url else ""
                parts.append(
                    f"<p><strong>{index}. {title}{html_escape(suffix)}</strong><br/>"
                    f"{image_html}"
                    f"内容：{content}<br/>{link_html}</p>"
                )

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
        summary = self.build_summary(articles, hot_topics, hours)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "window_hours": hours,
            "source_urls": source_urls,
            "themes": themes,
            "title": self.build_title(themes, hot_topics),
            "summary": summary,
            "short_video_script": self.build_short_video_script(articles, hot_topics, hours),
            "social_post": self.build_social_post(articles, hot_topics, hours),
            "articles": [asdict(article) for article in articles],
            "fetch_failures": failures,
            "hot_topics": [asdict(topic) for topic in hot_topics],
            "hot_topic_failures": hot_topic_failures,
        }

    def build_markdown(self, payload: dict) -> str:
        key_hot_topics = self.select_key_hot_topics(payload.get("hot_topics", []), limit=8)
        lines = [
            f"# {payload.get('title') or '国内外热点总结分析'}",
            "",
            f"生成时间：{self.format_iso_datetime(payload['generated_at'])}",
            f"统计窗口：近 {payload['window_hours']} 小时",
            "",
            "## 总体概览",
            payload["summary"],
            "",
            "## 当前主线",
        ]

        if payload["themes"]:
            for theme in payload["themes"]:
                lines.append(f"- {theme}")
        else:
            lines.append("- 市场波动")

        lines.extend(["", "## 短视频口播文案", payload["short_video_script"], "", "## 社媒短文案", payload["social_post"]])
        lines.extend(["", "## 海外热点简讯"])

        for index, article in enumerate(payload["articles"], start=1):
            lines.append(f"{index}. [{article['theme']}] {article['title']}")
            if article.get("image"):
                lines.append(f"![热点配图]({article['image']})")
            lines.append(f"内容：{self.build_article_brief(article)}")
            lines.append(f"链接：{article['link']}")
            lines.append("")

        if key_hot_topics:
            lines.append("## 国内热点分析")
            for topic in key_hot_topics:
                rank = topic.get("rank")
                rank_text = f"#{rank}" if isinstance(rank, int) and rank > 0 else "未标注排名"
                hot = topic.get("hot") or "热度未知"
                lines.append(f"- [{topic['platform']}] {topic['title']} | 排名：{rank_text} | 热度：{hot}")
                if topic.get("image"):
                    lines.append(f"  ![热点配图]({topic['image']})")
                lines.append(f"  内容：{self.build_hot_topic_analysis(topic)}")
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


class DigestLLMRefiner:
    """Refine generated copywriting with an optional LLM call."""

    def __init__(self, args) -> None:
        self.enabled = bool(getattr(args, "llm_enabled", False))
        self.provider = str(getattr(args, "llm_provider", "") or "openai").strip() or "openai"
        self.base_url = str(getattr(args, "llm_base_url", "") or "").strip() or "https://api.openai.com/v1"
        self.api_key = str(getattr(args, "llm_api_key", "") or "").strip()
        self.model = str(getattr(args, "llm_model", "") or "").strip()
        self.timeout = int(getattr(args, "llm_timeout", 25) or 25)
        self.article_scoring_prompt_path = Path(
            getattr(args, "llm_article_scoring_prompt_md", DEFAULT_LLM_ARTICLE_SCORING_PROMPT_MD)
            or DEFAULT_LLM_ARTICLE_SCORING_PROMPT_MD
        )
        self.copywriting_prompt_path = Path(
            getattr(args, "llm_copywriting_prompt_md", DEFAULT_LLM_COPYWRITING_PROMPT_MD)
            or DEFAULT_LLM_COPYWRITING_PROMPT_MD
        )
        llm_config_path = str(getattr(args, "llm_config", "") or "").strip()
        self.llm_config_path = Path(llm_config_path) if llm_config_path else None
        self.llm_config = self._load_llm_config()

    def _load_llm_config(self) -> dict[str, Any]:
        if not self.llm_config_path:
            return {}
        try:
            content = self.llm_config_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            LOGGER.warning("llm config json not found, use built-in strategy: %s", exc)
            return {}
        if not content:
            LOGGER.warning("llm config json is empty, use built-in strategy")
            return {}
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            LOGGER.warning("llm config json invalid, use built-in strategy: %s", exc)
            return {}
        if not isinstance(parsed, dict):
            LOGGER.warning("llm config json root is not object, use built-in strategy")
            return {}
        return parsed

    def _build_article_scoring_policy(self) -> dict[str, Any]:
        section = self.llm_config.get("article_scoring")
        if not isinstance(section, dict):
            return {}

        policy: dict[str, Any] = {}
        goal = str(section.get("goal") or "").strip()
        if goal:
            policy["goal"] = goal

        instruction = str(section.get("selection_instruction") or "").strip()
        if instruction:
            policy["selection_instruction"] = instruction

        raw_dimensions = section.get("dimensions")
        dimensions: list[dict[str, Any]] = []
        if isinstance(raw_dimensions, list):
            for item in raw_dimensions:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                description = str(item.get("description") or "").strip()
                weight_value = item.get("weight")
                if not name:
                    continue
                dimension: dict[str, Any] = {"name": name}
                try:
                    dimension["weight"] = int(weight_value)
                except (TypeError, ValueError):
                    pass
                if description:
                    dimension["description"] = description
                dimensions.append(dimension)
        if dimensions:
            policy["dimensions"] = dimensions
        return policy

    def _build_copywriting_policy(self) -> dict[str, Any]:
        section = self.llm_config.get("copywriting")
        if not isinstance(section, dict):
            return {}

        policy: dict[str, Any] = {}
        audience = str(section.get("audience") or "").strip()
        if audience:
            policy["audience"] = audience

        tone = str(section.get("tone") or "").strip()
        if tone:
            policy["tone"] = tone

        raw_requirements = section.get("requirements")
        requirements: list[str] = []
        if isinstance(raw_requirements, list):
            for item in raw_requirements:
                text = str(item or "").strip()
                if text:
                    requirements.append(text)
        if requirements:
            policy["requirements"] = requirements

        return policy

    def can_run(self) -> bool:
        return self.enabled and bool(self.api_key) and bool(self.model)

    def _build_article_scoring_messages(self, articles: list[Article], select_limit: int) -> list[dict[str, str]]:
        candidates = [
            {
                "index": index,
                "title": article.title,
                "source": article.source,
                "region": article.region,
                "theme": article.theme,
                "age_hours": article.age_hours,
                "base_score": article.score,
                "rationale": article.rationale,
            }
            for index, article in enumerate(articles, start=1)
        ]
        template = self._load_article_scoring_prompt_template()
        system_prompt, user_prompt_template = self._split_prompt_template(template)
        policy = self._build_article_scoring_policy()
        policy_json = json.dumps(policy, ensure_ascii=False, indent=2) if policy else "{}"
        user_prompt = user_prompt_template.replace(
            "{{select_limit}}",
            str(select_limit),
        ).replace(
            "{{output_schema}}",
            json.dumps({"ranked": [{"index": 1, "score": 88, "reason": "..."}]}, ensure_ascii=False, indent=2),
        ).replace(
            "{{candidates_json}}",
            json.dumps(candidates, ensure_ascii=False, indent=2),
        ).replace(
            "{{scoring_policy_json}}",
            policy_json,
        )
        if policy and "{{scoring_policy_json}}" not in user_prompt_template:
            user_prompt = (
                f"{user_prompt}\n\n"
                "补充评分策略（来自 llm-config）：\n"
                f"{policy_json}"
            )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def select_articles(self, articles: list[Article], select_limit: int) -> list[Article]:
        if not articles:
            return []

        limit = max(1, min(select_limit, len(articles)))
        default_selected = articles[:limit]

        if not self.can_run():
            if self.enabled and not self.api_key:
                LOGGER.warning("LLM article scoring skipped: missing api key")
            if self.enabled and not self.model:
                LOGGER.warning("LLM article scoring skipped: missing model")
            return default_selected

        try:
            messages = self._build_article_scoring_messages(articles, limit)
            content = self._request_completion(messages)
            output = self._parse_result(content)
            ranked = output.get("ranked")
            if not isinstance(ranked, list) or not ranked:
                raise ValueError("LLM article scoring response missing ranked list")

            llm_scores: dict[int, tuple[int, str]] = {}
            for item in ranked:
                if not isinstance(item, dict):
                    continue
                raw_index = item.get("index")
                if not isinstance(raw_index, int):
                    try:
                        raw_index = int(raw_index)
                    except (TypeError, ValueError):
                        continue
                if raw_index < 1 or raw_index > len(articles):
                    continue

                raw_score = item.get("score")
                try:
                    score = int(float(raw_score))
                except (TypeError, ValueError):
                    continue
                score = max(0, min(100, score))
                reason = str(item.get("reason") or "").strip()

                current = llm_scores.get(raw_index)
                if current is None or score > current[0]:
                    llm_scores[raw_index] = (score, reason)

            if not llm_scores:
                raise ValueError("LLM article scoring has no valid entries")

            decorated: list[tuple[int, int, int, Article]] = []
            for index, article in enumerate(articles, start=1):
                llm_score, llm_reason = llm_scores.get(index, (-1, ""))
                merged_rationale = article.rationale
                if llm_reason:
                    merged_rationale = f"{article.rationale}；AI研判：{llm_reason}"
                merged_article = replace(article, rationale=merged_rationale)
                decorated.append((llm_score, article.score, index, merged_article))

            decorated.sort(key=lambda item: (-item[0], -item[1], item[2]))
            selected = [item[3] for item in decorated[:limit]]
            LOGGER.info("llm article scoring completed, selected %d of %d", len(selected), len(articles))
            return selected
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("LLM article scoring failed, fallback to rule-based ranking: %s", exc)
            return default_selected

    def _build_context(self, payload: dict) -> dict[str, Any]:
        articles = payload.get("articles", [])
        hot_topics = payload.get("hot_topics", [])
        return {
            "title": str(payload.get("title") or ""),
            "window_hours": int(payload.get("window_hours") or 24),
            "themes": [str(item) for item in payload.get("themes", [])[:4]],
            "summary": str(payload.get("summary") or ""),
            "short_video_script": str(payload.get("short_video_script") or ""),
            "social_post": str(payload.get("social_post") or ""),
            "articles": [
                {
                    "title": str(item.get("title") or ""),
                    "summary": str(item.get("summary") or ""),
                    "focus_companies": str(item.get("focus_companies") or ""),
                    "source": str(item.get("source") or ""),
                    "region": str(item.get("region") or ""),
                    "theme": str(item.get("theme") or ""),
                    "score": int(item.get("score") or 0),
                    "published_at": str(item.get("published_at") or ""),
                    "rationale": str(item.get("rationale") or ""),
                }
                for item in articles[:8]
                if isinstance(item, dict)
            ],
            "hot_topics": [
                {
                    "platform": str(item.get("platform") or ""),
                    "rank": int(item.get("rank") or 0),
                    "title": str(item.get("title") or ""),
                    "summary": str(item.get("summary") or ""),
                    "hot": str(item.get("hot") or ""),
                }
                for item in hot_topics[:8]
                if isinstance(item, dict)
            ],
        }

    def _extract_json_text(self, text: str) -> str:
        content = text.strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z0-9_\-]*\n", "", content)
            content = re.sub(r"\n```$", "", content)
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return content[start : end + 1]
        return content

    def _parse_result(self, text: str) -> dict[str, Any]:
        parsed = json.loads(self._extract_json_text(text))
        if not isinstance(parsed, dict):
            raise ValueError("LLM response is not a JSON object")
        return parsed

    def _load_copywriting_prompt_template(self) -> str:
        default_template = (
            "# System Prompt\n"
            "你是财经内容编辑。你要根据输入的市场信息，输出简洁、有信息密度、避免夸张的中文文案。"
            "只输出 JSON，不要输出解释。\n\n"
            "# User Prompt\n"
            "请基于以下数据改写文案。\n"
            "1. summary 为一句话总览。\n"
            "2. headline_candidates 输出 3 条标题。\n"
            "3. short_video_script 适合口播。\n"
            "4. social_post 适合社媒发布。\n"
            "5. 避免编造未出现的数据。\n\n"
            "输出 JSON 结构：\n{{output_schema}}\n\n"
            "输入数据：\n{{input_data}}\n"
        )
        try:
            content = self.copywriting_prompt_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            LOGGER.warning("copywriting prompt markdown not found, use default prompt: %s", exc)
            return default_template
        return content or default_template

    def _load_article_scoring_prompt_template(self) -> str:
        default_template = (
            "# System Prompt\n"
            "你是海外市场内容总编。你需要从候选新闻中挑选最值得做成公众号日报的条目。"
            "评分标准看：市场影响力、时效性、来源可信度、对读者决策价值。"
            "不要编造事实，只输出 JSON。\n\n"
            "# User Prompt\n"
            "请对每条候选新闻打分（0-100），并给出一句中文理由。\n"
            "最终至少返回前 {{select_limit}} 条排序结果。\n\n"
            "输出 JSON 结构：\n{{output_schema}}\n\n"
            "候选新闻：\n{{candidates_json}}\n"
        )
        try:
            content = self.article_scoring_prompt_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            LOGGER.warning("article scoring prompt markdown not found, use default prompt: %s", exc)
            return default_template
        return content or default_template

    def _split_prompt_template(self, template: str) -> tuple[str, str]:
        system_marker = "# System Prompt"
        user_marker = "# User Prompt"
        if system_marker not in template or user_marker not in template:
            return (
                "你是财经内容编辑。你要根据输入的市场信息，输出简洁、有信息密度、避免夸张的中文文案。只输出 JSON，不要输出解释。",
                template,
            )

        system_start = template.index(system_marker) + len(system_marker)
        user_start = template.index(user_marker)
        system_prompt = template[system_start:user_start].strip()
        user_prompt = template[user_start + len(user_marker) :].strip()
        return system_prompt, user_prompt

    def _build_messages(self, payload: dict) -> list[dict[str, str]]:
        context = self._build_context(payload)
        copywriting_policy = self._build_copywriting_policy()
        if copywriting_policy:
            context["copywriting_policy"] = copywriting_policy
        schema_hint = {
            "title": "string, a polished article title",
            "summary": "string, 1 sentence",
            "short_video_script": "string, around 40-90 Chinese chars",
            "social_post": "string, around 40-120 Chinese chars",
        }
        template = self._load_copywriting_prompt_template()
        system_prompt, user_prompt_template = self._split_prompt_template(template)
        policy_json = json.dumps(copywriting_policy, ensure_ascii=False, indent=2) if copywriting_policy else "{}"
        user_prompt = user_prompt_template.replace(
            "{{output_schema}}",
            json.dumps(schema_hint, ensure_ascii=False, indent=2),
        ).replace(
            "{{input_data}}",
            json.dumps(context, ensure_ascii=False, indent=2),
        ).replace(
            "{{copywriting_policy_json}}",
            policy_json,
        )
        if copywriting_policy and "{{copywriting_policy_json}}" not in user_prompt_template:
            user_prompt = (
                f"{user_prompt}\n\n"
                "补充改写策略（来自 llm-config）：\n"
                f"{policy_json}"
            )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _request_completion(self, messages: list[dict[str, str]]) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        request_payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 900,
        }
        request = Request(
            url,
            data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "User-Agent": USER_AGENT,
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            response_text = ""
            try:
                response_text = exc.read().decode("utf-8", errors="ignore").strip()
            except Exception:  # noqa: BLE001
                response_text = ""
            detail = response_text or exc.reason or "no response body"
            raise RuntimeError(
                "LLM request failed "
                f"provider={self.provider} model={self.model} base_url={self.base_url} "
                f"status={exc.code} detail={detail}"
            ) from exc
        choices = raw.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError(f"LLM response missing choices: {raw}")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else ""
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"LLM response missing content: {raw}")
        return content

    def _sanitize_output(self, output: dict[str, Any], fallback: dict) -> dict[str, Any]:
        refined: dict[str, Any] = {}

        title = str(output.get("title") or "").strip()
        refined["title"] = title or str(fallback.get("title") or "")

        summary = str(output.get("summary") or "").strip()
        refined["summary"] = summary or str(fallback.get("summary") or "")

        short_video_script = str(output.get("short_video_script") or "").strip()
        refined["short_video_script"] = short_video_script or str(fallback.get("short_video_script") or "")

        social_post = str(output.get("social_post") or "").strip()
        refined["social_post"] = social_post or str(fallback.get("social_post") or "")

        return refined

    def refine_payload(self, payload: dict) -> dict:
        payload["llm_refined"] = False

        if not self.enabled:
            return payload
        if not self.api_key:
            LOGGER.warning("LLM refinement skipped: missing api key")
            return payload
        if not self.model:
            LOGGER.warning("LLM refinement skipped: missing model")
            return payload

        try:
            messages = self._build_messages(payload)
            content = self._request_completion(messages)
            output = self._parse_result(content)
            refined = self._sanitize_output(output, payload)

            payload["title"] = refined["title"]
            payload["summary"] = refined["summary"]
            payload["short_video_script"] = refined["short_video_script"]
            payload["social_post"] = refined["social_post"]
            payload["llm_refined"] = True

            LOGGER.info("llm refinement completed with model=%s", self.model)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("LLM refinement failed, fallback to rule-based copy: %s", exc)

        return payload


class DigestPublisher:
    """Publishes payload to local files and optional external channels."""

    AUTO_COVER_ENABLED = os.getenv("WECHAT_AUTO_COVER_ENABLED", "1") != "0"

    def __init__(self) -> None:
        self.renderer = DigestRenderer()

    def write_file(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def build_wechat_digest(self, summary: str) -> str:
        max_chars = int(os.getenv("WECHAT_DIGEST_MAX_CHARS", "120") or "120")
        max_chars = max(20, max_chars)
        text = re.sub(r"\s+", " ", str(summary or "")).strip()
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1].rstrip(" ，。；;,:：") + "…"

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

    def _load_cover_font(self, size: int) -> ImageFont.ImageFont:
        candidates = (
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        )
        for path in candidates:
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
        return ImageFont.load_default()

    def _safe_draw_text(self, text: str, font: ImageFont.ImageFont) -> str:
        cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
        if not cleaned:
            return ""
        try:
            cleaned.encode("latin-1")
            return cleaned
        except UnicodeEncodeError:
            # Bitmap fallback font may not support CJK glyphs.
            if not hasattr(font, "path"):
                return re.sub(r"[^\x20-\x7E]", " ", cleaned).strip()
            return cleaned

    def _wrap_text(self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
        if not text:
            return []
        words = text.split(" ")
        lines: list[str] = []
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            width = int(draw.textlength(trial, font=font))
            if width <= max_width or not current:
                current = trial
                continue
            lines.append(current)
            current = word
        if current:
            lines.append(current)
        return lines

    def generate_auto_wechat_cover(self, payload: dict) -> bytes:
        canvas = Image.new("RGB", (WECHAT_COVER_WIDTH, WECHAT_COVER_HEIGHT), (16, 30, 58))
        draw = ImageDraw.Draw(canvas)

        for y in range(WECHAT_COVER_HEIGHT):
            ratio = y / max(1, WECHAT_COVER_HEIGHT - 1)
            r = int(16 + (58 - 16) * ratio)
            g = int(30 + (76 - 30) * ratio)
            b = int(58 + (112 - 58) * ratio)
            draw.line([(0, y), (WECHAT_COVER_WIDTH, y)], fill=(r, g, b))

        draw.rounded_rectangle(
            [(60, 50), (WECHAT_COVER_WIDTH - 60, WECHAT_COVER_HEIGHT - 50)],
            radius=28,
            fill=(255, 255, 255),
        )

        title_font = self._load_cover_font(50)
        sub_font = self._load_cover_font(30)
        tiny_font = self._load_cover_font(24)

        title = self._safe_draw_text(str(payload.get("title") or "海外热点股市日报"), title_font)
        if not title:
            title = "Auto Market Digest"

        themes = [str(item).strip() for item in payload.get("themes", []) if str(item).strip()]
        subtitle = " / ".join(themes[:3]) if themes else "Global markets | Magnificent Seven"
        subtitle = self._safe_draw_text(subtitle, sub_font)

        generated = "生成时间 " + self.renderer.format_iso_datetime(str(payload.get("generated_at") or ""))
        generated = self._safe_draw_text(generated, tiny_font)

        max_text_width = WECHAT_COVER_WIDTH - 160
        title_lines = self._wrap_text(draw, title, title_font, max_text_width)[:2]
        if title_lines:
            y = 120
            for line in title_lines:
                draw.text((80, y), line, fill=(15, 33, 64), font=title_font)
                y += 64

        subtitle_lines = self._wrap_text(draw, subtitle, sub_font, max_text_width)[:2]
        if subtitle_lines:
            y = 260
            for line in subtitle_lines:
                draw.text((80, y), line, fill=(46, 86, 132), font=sub_font)
                y += 42

        if generated:
            draw.text((80, WECHAT_COVER_HEIGHT - 96), generated, fill=(67, 111, 156), font=tiny_font)

        buffer = io.BytesIO()
        canvas.save(buffer, format="JPEG", quality=92, optimize=True)
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

        if self.AUTO_COVER_ENABLED:
            LOGGER.info("no remote cover available, generating auto cover image")
            auto_cover_bytes = self.generate_auto_wechat_cover(payload)
            media_id = self.upload_wechat_image_bytes(access_token, auto_cover_bytes)
            LOGGER.info("wechat auto cover uploaded successfully")
            return media_id

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
                        "digest": self.build_wechat_digest(str(payload.get("summary") or "")),
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

    MAGNIFICENT_SEVEN_MIN_ARTICLES = int(os.getenv("MAGNIFICENT_SEVEN_MIN_ARTICLES", "3") or "3")
    MAGNIFICENT_SEVEN_FALLBACK_HOURS = int(os.getenv("MAGNIFICENT_SEVEN_FALLBACK_HOURS", "48") or "48")

    def __init__(self, args) -> None:
        self.args = args
        self.fetcher = DigestFetcher()
        self.renderer = DigestRenderer()
        self.llm_refiner = DigestLLMRefiner(args)
        self.publisher = DigestPublisher()

    def run(self) -> int:
        LOGGER.info("digest run started")
        effective_hours = int(self.args.hours)
        articles, failures, source_urls = self.fetcher.collect_articles(effective_hours)

        if self.fetcher.MAGNIFICENT_SEVEN_ONLY:
            min_articles = max(1, self.MAGNIFICENT_SEVEN_MIN_ARTICLES)
            fallback_hours = max(effective_hours, self.MAGNIFICENT_SEVEN_FALLBACK_HOURS)
            if len(articles) < min_articles and fallback_hours > effective_hours:
                LOGGER.info(
                    "magnificent-seven fallback triggered: article_count=%d < min=%d, retry with %dh window",
                    len(articles),
                    min_articles,
                    fallback_hours,
                )
                fallback_articles, fallback_failures, fallback_source_urls = self.fetcher.collect_articles(
                    fallback_hours
                )
                if len(fallback_articles) > len(articles):
                    articles = fallback_articles
                    effective_hours = fallback_hours
                if fallback_failures:
                    failures.extend(item for item in fallback_failures if item not in failures)
                if fallback_source_urls:
                    source_urls = list(dict.fromkeys([*source_urls, *fallback_source_urls]))

        candidate_articles = articles[: self.args.limit]
        articles = self.llm_refiner.select_articles(candidate_articles, self.args.select_limit)
        hot_topics, hot_topic_failures = self.fetcher.collect_hot_topics(self.args.hot_limit)

        if not articles and self.args.strict_fetch:
            reason = " | ".join(failures) if failures else "No eligible foreign market articles found."
            raise RuntimeError(reason)

        payload = self.renderer.build_payload(
            articles=articles,
            hot_topics=hot_topics,
            source_urls=source_urls,
            hours=effective_hours,
            failures=failures,
            hot_topic_failures=hot_topic_failures,
        )
        payload = self.llm_refiner.refine_payload(payload)

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
