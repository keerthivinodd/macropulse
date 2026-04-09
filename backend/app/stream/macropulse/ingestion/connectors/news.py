"""
News connectors — Newsdata.io, GNews, Gulf News RSS fallback.
Includes HTML cleaner and rules-based entity tagger.
"""
import asyncio
import html
import os
import re
from datetime import datetime, timezone

import httpx

import app.stream.macropulse.ingestion.config  # noqa: F401

try:
    import feedparser
    _FEEDPARSER_AVAILABLE = True
except ImportError:
    _FEEDPARSER_AVAILABLE = False

NEWSDATA_URL = "https://newsdata.io/api/1/news"
GNEWS_URL = "https://gnews.io/api/v4/search"
GULF_NEWS_RSS = "https://gulfnews.com/rss/business.xml"

# ---------------------------------------------------------------------------
# HTML cleaner
# ---------------------------------------------------------------------------

def strip_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", text)
    return html.unescape(cleaned).strip()


# ---------------------------------------------------------------------------
# Entity tagger
# ---------------------------------------------------------------------------

_ENTITY_RULES: list[tuple[list[str], str]] = [
    (["RBI", "repo rate", "MPC"], "RBI"),
    (["SAMA", "SAIBOR"], "SAMA"),
    (["CBUAE", "EIBOR"], "CBUAE"),
    (["crude", "Brent", "WTI", "oil"], "crude_oil"),
    (["USD/INR", "rupee", "INR"], "fx_inr"),
    (["inflation", "WPI", "CPI"], "inflation"),
    (["interest rate", "rate hike"], "interest_rate"),
]


def tag_entities(text: str) -> list[str]:
    """Rules-based entity tagger. Returns list of matched entity tags."""
    if not text:
        return []
    tags: list[str] = []
    for keywords, tag in _ENTITY_RULES:
        if any(kw.lower() in text.lower() for kw in keywords):
            tags.append(tag)
    return tags


# ---------------------------------------------------------------------------
# Individual source fetchers
# ---------------------------------------------------------------------------

async def _fetch_newsapi(client: httpx.AsyncClient) -> list[dict]:
    try:
        resp = await client.get(
            NEWSDATA_URL,
            params={
                "q": "RBI OR repo rate OR inflation OR crude oil OR FX",
                "language": "en",
                "country": "in",
                "apikey": os.getenv("NEWSDATA_API_KEY", ""),
            },
        )
        resp.raise_for_status()
        articles = resp.json().get("results", [])
        return [
            {
                "title": strip_html(a.get("title", "")),
                "description": strip_html(a.get("description") or a.get("content", "")),
                "url": a.get("link", ""),
                "published_at": _parse_dt(a.get("pubDate")),
                "source_name": a.get("source_id", "newsdata"),
                "language": "en",
                "tags": tag_entities(
                    f"{a.get('title', '')} {a.get('description', '')}"
                ),
                "embedded": False,
            }
            for a in articles
            if a.get("link")
        ]
    except Exception:
        return []


async def _fetch_gnews(client: httpx.AsyncClient) -> list[dict]:
    try:
        resp = await client.get(
            GNEWS_URL,
            params={
                "q": "RBI monetary policy OR SAMA OR CBUAE OR commodity price",
                "lang": "en",
                "country": "in",
                "max": 20,
                "apikey": os.getenv("GNEWS_KEY", ""),
            },
        )
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        return [
            {
                "title": strip_html(a.get("title", "")),
                "description": strip_html(a.get("description", "")),
                "url": a.get("url", ""),
                "published_at": _parse_dt(a.get("publishedAt")),
                "source_name": a.get("source", {}).get("name", "gnews"),
                "language": "en",
                "tags": tag_entities(
                    f"{a.get('title', '')} {a.get('description', '')}"
                ),
                "embedded": False,
            }
            for a in articles
            if a.get("url")
        ]
    except Exception:
        return []


async def _fetch_gulf_rss(client: httpx.AsyncClient) -> list[dict]:
    if not _FEEDPARSER_AVAILABLE:
        return []
    try:
        resp = await client.get(GULF_NEWS_RSS)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        results = []
        for entry in feed.entries:
            title = strip_html(entry.get("title", ""))
            desc = strip_html(entry.get("summary", ""))
            url = entry.get("link", "")
            if not url:
                continue
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                import time as _time
                published_at = datetime.fromtimestamp(
                    _time.mktime(entry.published_parsed), tz=timezone.utc
                )
            results.append({
                "title": title,
                "description": desc,
                "url": url,
                "published_at": published_at,
                "source_name": "Gulf News",
                "language": "en",
                "tags": tag_entities(f"{title} {desc}"),
                "embedded": False,
            })
        return results
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Main aggregator
# ---------------------------------------------------------------------------

async def fetch_all_news(client: httpx.AsyncClient | None = None) -> list[dict]:
    """Fetch from all sources in parallel, deduplicate by URL."""
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=20.0, trust_env=False)
    try:
        newsapi, gnews, gulf = await asyncio.gather(
            _fetch_newsapi(client),
            _fetch_gnews(client),
            _fetch_gulf_rss(client),
        )
        all_articles = newsapi + gnews + gulf
        # Deduplicate by URL
        seen: set[str] = set()
        unique: list[dict] = []
        for a in all_articles:
            if a["url"] and a["url"] not in seen:
                seen.add(a["url"])
                unique.append(a)
        return unique
    finally:
        if owns_client:
            await client.aclose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


async def _main() -> None:
    articles = await fetch_all_news()
    print(f"Fetched {len(articles)} articles")
    for a in articles[:3]:
        print(a)


if __name__ == "__main__":
    asyncio.run(_main())
