from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FeedSource:
    label: str
    urls: tuple[str, ...] = ()
    queries: tuple[str, ...] = ()
    weight: int = 1


@dataclass(frozen=True)
class HotTopicSource:
    name: str
    source_type: str


USER_AGENT = "Mozilla/5.0 (compatible; auto-video/1.0; +https://github.com/)"
DEFAULT_OUTPUT_JSON = Path("output/foreign_market_hotspots.json")
DEFAULT_OUTPUT_MD = Path("output/foreign_market_copy.md")
DEFAULT_LOG_DIR = Path("logs")
GOOGLE_NEWS_BASE = "https://news.google.com/rss/search"
PUSHPLUS_URL = "https://www.pushplus.plus/send"
WECHAT_ACCESS_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
WECHAT_ADD_DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
WECHAT_ADD_MATERIAL_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"
DEFAULT_WECHAT_AUTHOR = "Auto Video"
DEFAULT_WECHAT_THUMB_CACHE = Path("output/wechat_thumb_cache.json")
WECHAT_COVER_WIDTH = 900
WECHAT_COVER_HEIGHT = 500
WECHAT_RETRYABLE_DRAFT_ERRCODES = {40007, 53401, 53402}
HOT_TOPIC_API_BASE = "https://dabenshi.cn/other/api/hot.php?type="
WECHAT_COVER_MIN_WIDTH = 640
WECHAT_COVER_MIN_HEIGHT = 360

FINANCE_IMAGE_HOST_KEYWORDS: tuple[str, ...] = (
    "cnbc.com",
    "reuters.com",
    "bloomberg.com",
    "marketwatch.com",
    "wsj.com",
    "ft.com",
    "yahoo.com",
    "nasdaq.com",
    "investing.com",
    "barrons.com",
)


FEEDS: tuple[FeedSource, ...] = (
    FeedSource(
        label="US",
        urls=(
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "https://feeds.content.dowjones.io/public/rss/mw_topstories",
            "https://www.nasdaq.com/feed/rssoutbound?category=Markets",
            "https://feeds.marketwatch.com/marketwatch/topstories/",
        ),
        weight=3,
    ),
    FeedSource(
        label="Europe",
        urls=(
            "https://www.cnbc.com/id/100727362/device/rss/rss.html",
            "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
            "https://feeds.marketwatch.com/marketwatch/marketpulse/",
        ),
        queries=('("European stocks" OR "STOXX 600" OR FTSE OR DAX) when:1d',),
        weight=2,
    ),
    FeedSource(
        label="Asia",
        urls=(
            "https://www.cnbc.com/id/19832390/device/rss/rss.html",
            "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
        ),
        queries=('("Asian stocks" OR Nikkei OR Hang Seng OR "MSCI Asia") when:1d',),
        weight=2,
    ),
    FeedSource(
        label="Global",
        urls=(
            "https://www.cnbc.com/id/10000664/device/rss/rss.html",
            "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        ),
        queries=('(NASDAQ OR NYSE OR "S&P 500" OR "Dow Jones") when:1d',),
        weight=2,
    ),
)


THEMES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("利率与美联储", ("fed", "rate", "rates", "treasury", "bond", "yield", "powell")),
    ("科技与芯片", ("ai", "chip", "chips", "semiconductor", "nvidia", "tsmc", "tech")),
    ("财报与业绩", ("earnings", "profit", "revenue", "guidance", "quarter", "results")),
    ("通胀与宏观", ("inflation", "cpi", "ppi", "payrolls", "gdp", "recession", "macro")),
    ("能源与大宗", ("oil", "crude", "gas", "gold", "commodity", "opec")),
    ("监管与关税", ("tariff", "regulation", "antitrust", "ban", "sanction", "policy")),
    ("欧洲市场", ("europe", "euro", "stoxx", "ftse", "dax", "ecb")),
    ("亚洲市场", ("asia", "japan", "china", "hong kong", "nikkei", "hang seng")),
)


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


HOT_TOPIC_APIS: tuple[HotTopicSource, ...] = (
    HotTopicSource(name="抖音热点", source_type="douyinhot"),
    HotTopicSource(name="头条热榜", source_type="toutiaoHot"),
    HotTopicSource(name="百度热搜", source_type="baidu"),
)
