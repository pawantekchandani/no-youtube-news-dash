import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

import feedparser
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from newsdash.db.models import RawItem

logger = logging.getLogger(__name__)

CONCURRENCY_LIMIT = 10
REQUEST_TIMEOUT = 30
MAX_RETRIES = 2

UTM_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


def canonical_url(url: str) -> str:
    """Strip UTM params and trailing slashes for deduplication."""
    try:
        parsed = urlparse(url)
        params = {k: v for k, v in parse_qs(parsed.query).items() if k not in UTM_PARAMS}
        clean_query = urlencode(params, doseq=True)
        clean = parsed._replace(query=clean_query, fragment="")
        return urlunparse(clean).rstrip("/")
    except Exception:
        return url.rstrip("/")


def url_hash(url: str) -> str:
    return hashlib.sha256(canonical_url(url).encode()).hexdigest()


def parse_date(entry) -> Optional[datetime]:
    """Extract published date from a feedparser entry."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                continue
    return None


def extract_description(entry) -> str:
    """Get the best available description text, stripped of HTML."""
    for attr in ("summary", "description", "content"):
        val = getattr(entry, attr, None)
        if val:
            if isinstance(val, list) and val:
                val = val[0].get("value", "")
            text = re.sub(r"<[^>]+>", " ", str(val))
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                return text[:2000]
    return ""


async def fetch_feed(client: httpx.AsyncClient, feed: dict) -> list[dict]:
    """Fetch one RSS feed and return list of raw item dicts."""
    url = feed["url"]
    source_id = feed["id"]
    items = []

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            parsed = feedparser.parse(response.text)

            for entry in parsed.entries:
                item_url = getattr(entry, "link", None)
                title = getattr(entry, "title", "").strip()
                if not item_url or not title:
                    continue

                items.append({
                    "url": item_url,
                    "url_hash": url_hash(item_url),
                    "title": title,
                    "description": extract_description(entry),
                    "published_at": parse_date(entry),
                    "source_id": source_id,
                })
            logger.info(f"Fetched {len(items)} items from {source_id}")
            return items

        except httpx.HTTPStatusError as e:
            if e.response.status_code < 500:
                logger.warning(f"Client error {e.response.status_code} for {source_id}: {url}")
                return []
            if attempt < MAX_RETRIES:
                await asyncio.sleep(5 * (attempt + 1))
        except Exception as e:
            if attempt < MAX_RETRIES:
                logger.warning(f"Attempt {attempt+1} failed for {source_id}: {e}")
                await asyncio.sleep(5 * (attempt + 1))
            else:
                logger.error(f"All attempts failed for {source_id}: {e}")

    return []


async def store_raw_items(session: AsyncSession, items: list[dict]) -> int:
    """Store new raw items, skipping duplicates. Returns count stored."""
    stored = 0
    for item in items:
        existing = await session.execute(
            select(RawItem).where(RawItem.url_hash == item["url_hash"])
        )
        if existing.scalar_one_or_none():
            continue
        raw = RawItem(**item)
        session.add(raw)
        stored += 1
    await session.commit()
    return stored


async def run_rss_fetch(session: AsyncSession, feeds: list[dict]) -> int:
    """Fetch all enabled RSS feeds concurrently. Returns total items stored."""
    enabled_feeds = [f for f in feeds if f.get("enabled", True)]
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async def bounded_fetch(client, feed):
        async with semaphore:
            return await fetch_feed(client, feed)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [bounded_fetch(client, feed) for feed in enabled_feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items = []
    for result in results:
        if isinstance(result, list):
            all_items.extend(result)
        else:
            logger.error(f"Feed fetch raised exception: {result}")

    total_stored = await store_raw_items(session, all_items)
    logger.info(f"RSS fetch complete: {len(all_items)} fetched, {total_stored} new")
    return total_stored
