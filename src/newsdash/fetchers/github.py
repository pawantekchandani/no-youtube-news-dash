import hashlib
import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from newsdash.db.models import Article

logger = logging.getLogger(__name__)

GITHUB_TRENDING_URL = "https://github.com/trending/{language}?since={time_range}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def repo_url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


async def scrape_trending(language: str, time_range: str) -> list[dict]:
    """Scrape GitHub Trending for one language."""
    url = GITHUB_TRENDING_URL.format(language=language, time_range=time_range)
    repos = []

    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
            response = await client.get(url, timeout=30)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        repo_list = soup.select("article.Box-row")

        for repo in repo_list:
            name_el = repo.select_one("h2 a")
            if not name_el:
                continue

            repo_path = name_el.get("href", "").strip("/")
            repo_url = f"https://github.com/{repo_path}"
            repo_name = repo_path.replace("/", " / ")

            desc_el = repo.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            stars_el = repo.select_one("span.d-inline-block.float-sm-right")
            stars_today = stars_el.get_text(strip=True) if stars_el else ""

            repos.append({
                "url": repo_url,
                "url_hash": repo_url_hash(repo_url),
                "title": f"⭐ {repo_name} ({stars_today})",
                "summary": description or f"Trending {language} repository on GitHub",
                "summary_cached": True,
                "published_at": datetime.now(timezone.utc),
                "fetched_at": datetime.now(timezone.utc),
                "source_id": "github_trending",
                "source_name": "GitHub Trending",
                "source_tier": 1,
                "topic_id": "github_trending",
            })

        logger.info(f"GitHub Trending ({language}): {len(repos)} repos")
    except Exception as e:
        logger.error(f"GitHub Trending scrape failed for {language}: {e}")

    return repos


async def run_github_fetch(session: AsyncSession, github_config: dict) -> int:
    """Fetch GitHub trending for all configured languages."""
    if not github_config.get("enabled", True):
        return 0

    languages = github_config.get("languages", ["python"])
    time_range = github_config.get("time_range", "weekly")
    stored = 0

    for language in languages:
        repos = await scrape_trending(language, time_range)
        for repo in repos:
            existing = await session.execute(
                select(Article).where(Article.url_hash == repo["url_hash"])
            )
            if existing.scalar_one_or_none():
                continue
            article = Article(**repo)
            session.add(article)
            stored += 1

    await session.commit()
    logger.info(f"GitHub: {stored} new repos stored")
    return stored
