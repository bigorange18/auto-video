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


@dataclass(frozen=True)
class DomesticRssSource:
    name: str
    url: str


USER_AGENT = "Mozilla/5.0 (compatible; auto-video/1.0; +https://github.com/)"
DEFAULT_OUTPUT_JSON = Path("output/foreign_market_hotspots.json")
DEFAULT_OUTPUT_MD = Path("output/foreign_market_copy.md")
DEFAULT_LLM_CONFIG = Path("scripts/digest_llm_config.json")
DEFAULT_LLM_COPYWRITING_PROMPT_MD = Path("scripts/digest_copywriting_prompt.md")
DEFAULT_LLM_ARTICLE_SCORING_PROMPT_MD = Path("scripts/digest_article_scoring_prompt.md")
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_QWEN_MODEL = "qwen-plus"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
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
WSCN_LIVES_API_URL = "https://api-one-wscn.awtmt.com/apiv1/content/lives?channel=global-channel&page=1&limit=30"
BAIDU_HOT_API_TYPE = "baidu"
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
        label="US7",
        urls=(
            "https://www.nasdaq.com/feed/rssoutbound?symbol=AAPL",
            "https://www.nasdaq.com/feed/rssoutbound?symbol=MSFT",
            "https://www.nasdaq.com/feed/rssoutbound?symbol=GOOGL",
            "https://www.nasdaq.com/feed/rssoutbound?symbol=AMZN",
            "https://www.nasdaq.com/feed/rssoutbound?symbol=NVDA",
            "https://www.nasdaq.com/feed/rssoutbound?symbol=META",
            "https://www.nasdaq.com/feed/rssoutbound?symbol=TSLA",
        ),
        weight=4,
    ),
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
    ("美股七巨头", ("apple", "microsoft", "alphabet", "google", "amazon", "nvidia", "meta", "tesla")),
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


MAGNIFICENT_SEVEN_MAP: dict[str, tuple[str, ...]] = {
    "Apple": ("apple", "aapl"),
    "Microsoft": ("microsoft", "msft"),
    "Alphabet": ("alphabet", "google", "googl", "goog"),
    "Amazon": ("amazon", "amzn"),
    "Nvidia": ("nvidia", "nvda"),
    "Meta": ("meta", "facebook", "fb"),
    "Tesla": ("tesla", "tsla"),
}


HOT_TOPIC_APIS: tuple[HotTopicSource, ...] = (
    HotTopicSource(name="抖音热点", source_type="douyinhot"),
    HotTopicSource(name="头条热榜", source_type="toutiaoHot"),
    HotTopicSource(name="百度热搜", source_type="baidu"),
)


DOMESTIC_RSS_SOURCES: tuple[DomesticRssSource, ...] = (
    DomesticRssSource(name="中新网财经", url="https://www.chinanews.com.cn/rss/finance.xml"),
    DomesticRssSource(name="中新网滚动", url="https://www.chinanews.com.cn/rss/scroll-news.xml"),
)
