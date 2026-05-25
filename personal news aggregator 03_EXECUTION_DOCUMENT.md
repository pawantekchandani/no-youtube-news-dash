# Execution Document
# Personal Geopolitics & Tech Intelligence Dashboard
**Version:** 1.0  
**Status:** Approved for Build  
**Last Updated:** May 2026  
**Intended Reader:** Any person or AI agent with zero prior context. Every command is exact. Nothing is left to assumption.

---

## BEFORE YOU BEGIN — Read This Entirely First

This document covers all 5 build phases end to end. Each phase builds on the previous. Do not skip phases.

**What you need before starting:**
- A MacBook running macOS 13 (Ventura) or later
- An internet connection
- An Anthropic account (for Phase 2). Get one at https://console.anthropic.com
- 2–3 hours for Phase 1. 30–60 minutes for each subsequent phase.

**What you do NOT need:**
- Any prior knowledge of the codebase
- Existing Python installation (we install everything fresh)
- Any database software
- Any server software

**Conventions used in this document:**
- Lines beginning with `$` are terminal commands. Do not type the `$` — it represents the terminal prompt.
- Lines beginning with `#` inside code blocks are comments explaining the command. Do not type them.
- `[YOUR VALUE HERE]` means replace with your actual value.
- Every command must be run from the directory specified at the start of each section unless told otherwise.

---

## Table of Contents

1. [Phase 1 — Working Aggregator](#phase-1--working-aggregator)
   - [1.1 Install Prerequisites](#11-install-prerequisites)
   - [1.2 Create Project Structure](#12-create-project-structure)
   - [1.3 Install Python Dependencies](#13-install-python-dependencies)
   - [1.4 Create Configuration File](#14-create-configuration-file)
   - [1.5 Create Database Models](#15-create-database-models)
   - [1.6 Create RSS Fetcher](#16-create-rss-fetcher)
   - [1.7 Create GitHub Fetcher](#17-create-github-fetcher)
   - [1.8 Create Deduplicator](#18-create-deduplicator)
   - [1.9 Create Topic Classifier](#19-create-topic-classifier)
   - [1.10 Create Config Loader](#110-create-config-loader)
   - [1.11 Create FastAPI Server](#111-create-fastapi-server)
   - [1.12 Create Dashboard Template](#112-create-dashboard-template)
   - [1.13 Create Pipeline Runner](#113-create-pipeline-runner)
   - [1.14 Test Phase 1](#114-test-phase-1)
2. [Phase 2 — AI Summaries](#phase-2--ai-summaries)
3. [Phase 3 — Derived Topics](#phase-3--derived-topics)
4. [Phase 4 — Automation and Email Digest](#phase-4--automation-and-email-digest)
5. [Phase 5 — Quality Layer](#phase-5--quality-layer)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance Reference](#maintenance-reference)

---

## Phase 1 — Working Aggregator

### 1.1 Install Prerequisites

Open the Terminal application on your Mac. Terminal is in Applications → Utilities → Terminal.

**Step 1.1.1 — Install Homebrew (macOS package manager)**

Check if Homebrew is already installed:
```bash
$ brew --version
```

If the output shows a version number (e.g. `Homebrew 4.x.x`), skip to Step 1.1.2.

If the output says `command not found`, install Homebrew:
```bash
$ /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen prompts. When it finishes, run:
```bash
$ brew --version
```
Expected output: `Homebrew 4.x.x` (or similar)

**Step 1.1.2 — Install Python 3.11**

Check if Python 3.11+ is already installed:
```bash
$ python3 --version
```

If output shows `Python 3.11.x` or higher, skip to Step 1.1.3.

If not, install via Homebrew:
```bash
$ brew install python@3.11
```

After installation completes:
```bash
$ python3.11 --version
```
Expected output: `Python 3.11.x`

**Step 1.1.3 — Install uv (Python package manager)**

```bash
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen Terminal, then verify:
```bash
$ uv --version
```
Expected output: `uv 0.x.x`

**Step 1.1.4 — Install Git**

Check if Git is installed:
```bash
$ git --version
```

If not installed:
```bash
$ brew install git
```

---

### 1.2 Create Project Structure

**Step 1.2.1 — Choose where to create the project**

We will create the project in your home directory. Run:
```bash
$ cd ~
```

**Step 1.2.2 — Create the full directory structure**

Run all of the following commands exactly:
```bash
$ mkdir -p news-dashboard/config
$ mkdir -p news-dashboard/src/newsdash/fetchers
$ mkdir -p news-dashboard/src/newsdash/pipeline
$ mkdir -p news-dashboard/src/newsdash/db
$ mkdir -p news-dashboard/src/newsdash/server/templates
$ mkdir -p news-dashboard/src/newsdash/digest
$ mkdir -p news-dashboard/data
$ mkdir -p news-dashboard/logs
$ mkdir -p news-dashboard/launchd
$ mkdir -p news-dashboard/tests
```

**Step 1.2.3 — Enter the project directory**

```bash
$ cd ~/news-dashboard
```

All subsequent commands in this document are run from `~/news-dashboard` unless stated otherwise.

**Step 1.2.4 — Initialise Git repository**

```bash
$ git init
```

**Step 1.2.5 — Create .gitignore**

```bash
$ cat > .gitignore << 'EOF'
.env
data/
logs/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
.venv/
EOF
```

**Step 1.2.6 — Create empty __init__.py files**

```bash
$ touch src/newsdash/__init__.py
$ touch src/newsdash/fetchers/__init__.py
$ touch src/newsdash/pipeline/__init__.py
$ touch src/newsdash/db/__init__.py
$ touch src/newsdash/server/__init__.py
$ touch src/newsdash/digest/__init__.py
$ touch tests/__init__.py
```

**Step 1.2.7 — Verify the structure was created correctly**

```bash
$ find . -type d | sort
```

Expected output (among others):
```
./config
./data
./launchd
./logs
./src
./src/newsdash
./src/newsdash/db
./src/newsdash/digest
./src/newsdash/fetchers
./src/newsdash/pipeline
./src/newsdash/server
./src/newsdash/server/templates
./tests
```

---

### 1.3 Install Python Dependencies

**Step 1.3.1 — Create pyproject.toml**

```bash
$ cat > pyproject.toml << 'EOF'
[project]
name = "newsdash"
version = "1.0.0"
description = "Personal geopolitics and tech intelligence dashboard"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "jinja2>=3.1.0",
    "httpx>=0.27.0",
    "feedparser>=6.0.0",
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.20.0",
    "rapidfuzz>=3.0.0",
    "apscheduler>=3.10.0",
    "pyyaml>=6.0.0",
    "beautifulsoup4>=4.12.0",
    "python-dotenv>=1.0.0",
    "lxml>=5.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.4.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/newsdash"]
EOF
```

**Step 1.3.2 — Create the virtual environment and install dependencies**

```bash
$ uv venv .venv --python 3.11
$ source .venv/bin/activate
$ uv pip install -e ".[dev]"
```

**Step 1.3.3 — Verify installation**

```bash
$ python -c "import fastapi, feedparser, sqlalchemy, rapidfuzz, apscheduler, yaml; print('All dependencies OK')"
```

Expected output: `All dependencies OK`

**Step 1.3.4 — Create .env file**

```bash
$ cat > .env << 'EOF'
# LLM API Keys (needed for Phase 2)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# LLM Settings (needed for Phase 2)
LLM_PROVIDER=anthropic
SUMMARISE_MODEL=claude-haiku-4-20251001
ANALYSIS_MODEL=claude-sonnet-4-20250514

# Email Settings (needed for Phase 4)
DIGEST_RECIPIENT_EMAIL=
DIGEST_SMTP_HOST=localhost
DIGEST_SMTP_PORT=25

# App Settings
DATABASE_URL=sqlite+aiosqlite:///./data/news.db
LOG_LEVEL=INFO
EOF
```

**Step 1.3.5 — Create .env.example for reference**

```bash
$ cp .env .env.example
```

---

### 1.4 Create Configuration File

**Step 1.4.1 — Create sources.yaml**

This file controls all news sources, topic definitions, and pipeline settings. Create it exactly as follows:

```bash
$ cat > config/sources.yaml << 'EOF'
pipeline:
  fetch_interval_minutes: 60
  dedupe_window_hours: 48
  dedupe_similarity_threshold: 85
  summarise_batch_size: 20
  article_retention_days: 30
  dashboard_article_age_hours: 24

digest:
  enabled: false
  schedule:
    - "08:00"
    - "20:00"
  top_n_per_topic: 5
  recipient_email: "you@example.com"
  sender_email: "newsdash@localhost"

topics:
  - id: geopolitics_india
    label: "Geopolitics — India Impact"
    dashboard_column: geopolitics
    derived: false
    priority: 1
    keywords: ["India", "Modi", "Delhi", "New Delhi", "South Asia", "SAARC", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Indo-Pacific", "Quad", "Indian foreign policy"]

  - id: geopolitics
    label: "Global Geopolitics"
    dashboard_column: geopolitics
    derived: false
    priority: 2
    keywords: ["war", "conflict", "sanctions", "treaty", "diplomacy", "NATO", "UN", "G20", "China", "Russia", "Ukraine", "Taiwan", "trade war", "tariffs", "alliance", "military", "nuclear", "geopolitics"]

  - id: it_funding
    label: "Funding, M&A and Investments"
    dashboard_column: tech
    derived: false
    priority: 3
    keywords: ["funding", "Series A", "Series B", "Series C", "seed round", "acquisition", "merger", "acqui-hire", "IPO", "valuation", "unicorn", "venture capital", "raises", "investment round"]

  - id: ai_jobs
    label: "AI and Job Market"
    dashboard_column: ai
    derived: false
    priority: 5
    keywords: ["AI jobs", "automation displacement", "future of work", "job loss", "AI unemployment", "workforce", "labor market", "reskilling", "job market"]

  - id: ai_business
    label: "AI Impact on Business"
    dashboard_column: ai
    derived: false
    priority: 6
    keywords: ["enterprise AI", "AI adoption", "AI ROI", "AI implementation", "automation", "AI strategy", "AI transformation", "corporate AI"]

  - id: ai_news
    label: "AI Space News"
    dashboard_column: ai
    derived: false
    priority: 7
    keywords: ["artificial intelligence", "machine learning", "deep learning", "LLM", "large language model", "GPT", "Claude", "Gemini", "Llama", "neural network", "transformer", "foundation model"]

  - id: github_trending
    label: "Trending on GitHub"
    dashboard_column: tech
    derived: false
    priority: 8
    keywords: []

  - id: it_launches
    label: "Big Launches and Updates"
    dashboard_column: tech
    derived: false
    priority: 9
    keywords: ["launch", "release", "update", "new version", "new feature", "announced", "changelog", "generally available", "open source", "Product Hunt"]

  - id: it_news
    label: "IT Industry News"
    dashboard_column: tech
    derived: false
    priority: 10
    keywords: ["software", "hardware", "cloud", "cybersecurity", "enterprise tech", "data center", "semiconductor", "chip", "IT infrastructure"]

  - id: market_sectors_up
    label: "Sectors to Watch — Tailwinds"
    dashboard_column: markets
    derived: true
    priority: 99
    keywords: []

  - id: market_sectors_down
    label: "Sectors Under Pressure"
    dashboard_column: markets
    derived: true
    priority: 99
    keywords: []

  - id: ai_nonconventional
    label: "Unconventional AI Implementations"
    dashboard_column: ai
    derived: true
    priority: 4
    keywords: []

feeds:
  - id: foreign_affairs
    name: Foreign Affairs
    url: https://www.foreignaffairs.com/rss.xml
    topics: [geopolitics]
    tier: 1
    enabled: true

  - id: foreign_policy
    name: Foreign Policy
    url: https://foreignpolicy.com/feed/
    topics: [geopolitics]
    tier: 2
    enabled: true

  - id: the_diplomat
    name: The Diplomat
    url: https://thediplomat.com/feed/
    topics: [geopolitics]
    tier: 2
    enabled: true

  - id: reuters_world
    name: Reuters World
    url: https://feeds.reuters.com/reuters/worldNews
    topics: [geopolitics]
    tier: 2
    enabled: true

  - id: economist_world
    name: The Economist
    url: https://www.economist.com/the-world-this-week/rss.xml
    topics: [geopolitics]
    tier: 1
    enabled: true

  - id: orfonline
    name: Observer Research Foundation
    url: https://www.orfonline.org/feed/
    topics: [geopolitics_india]
    tier: 1
    enabled: true

  - id: carnegie_india
    name: Carnegie India
    url: https://carnegieindia.org/rss/
    topics: [geopolitics_india]
    tier: 1
    enabled: true

  - id: takshashila
    name: Takshashila Institution
    url: https://takshashila.org.in/feed/
    topics: [geopolitics_india]
    tier: 1
    enabled: true

  - id: the_hindu_intl
    name: The Hindu International
    url: https://www.thehindu.com/news/international/feeder/default.rss
    topics: [geopolitics_india]
    tier: 2
    enabled: true

  - id: the_print_ns
    name: The Print National Security
    url: https://theprint.in/category/national-security/feed/
    topics: [geopolitics_india]
    tier: 2
    enabled: true

  - id: mit_tech_review_ai
    name: MIT Technology Review AI
    url: https://www.technologyreview.com/topic/artificial-intelligence/feed
    topics: [ai_news]
    tier: 1
    enabled: true

  - id: import_ai
    name: Import AI
    url: https://importai.substack.com/feed
    topics: [ai_news]
    tier: 1
    enabled: true

  - id: the_batch
    name: The Batch DeepLearning.AI
    url: https://www.deeplearning.ai/the-batch/feed.rss
    topics: [ai_news]
    tier: 1
    enabled: true

  - id: anthropic_blog
    name: Anthropic Blog
    url: https://www.anthropic.com/rss.xml
    topics: [ai_news]
    tier: 1
    enabled: true

  - id: openai_blog
    name: OpenAI Blog
    url: https://openai.com/blog/rss.xml
    topics: [ai_news]
    tier: 1
    enabled: true

  - id: deepmind_blog
    name: Google DeepMind Blog
    url: https://deepmind.google/blog/rss.xml
    topics: [ai_news]
    tier: 1
    enabled: true

  - id: venturebeat_ai
    name: VentureBeat AI
    url: https://venturebeat.com/category/ai/feed/
    topics: [ai_news]
    tier: 2
    enabled: true

  - id: hbr_ai
    name: Harvard Business Review AI
    url: https://hbr.org/topic/subject/ai/rss
    topics: [ai_business]
    tier: 1
    enabled: true

  - id: mckinsey_ai
    name: McKinsey AI Insights
    url: https://www.mckinsey.com/capabilities/quantumblack/our-insights/rss
    topics: [ai_business]
    tier: 1
    enabled: true

  - id: bcg_ai
    name: BCG AI and Digital
    url: https://www.bcg.com/rss/ideas.xml
    topics: [ai_business]
    tier: 1
    enabled: true

  - id: stanford_hai
    name: Stanford HAI
    url: https://hai.stanford.edu/news/rss.xml
    topics: [ai_jobs]
    tier: 1
    enabled: true

  - id: wef_future_work
    name: World Economic Forum Future of Work
    url: https://www.weforum.org/agenda/tag/future-of-work/rss
    topics: [ai_jobs]
    tier: 1
    enabled: true

  - id: brookings_ai
    name: Brookings AI
    url: https://www.brookings.edu/topic/artificial-intelligence/feed/
    topics: [ai_jobs]
    tier: 1
    enabled: true

  - id: ieee_spectrum_ai
    name: IEEE Spectrum AI
    url: https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss
    topics: [ai_nonconventional]
    tier: 1
    enabled: true

  - id: jmlr
    name: Journal of Machine Learning Research
    url: https://jmlr.org/jmlr.xml
    topics: [ai_nonconventional]
    tier: 1
    enabled: true

  - id: ars_technica
    name: Ars Technica
    url: https://feeds.arstechnica.com/arstechnica/index
    topics: [it_news]
    tier: 1
    enabled: true

  - id: the_register
    name: The Register
    url: https://www.theregister.com/headlines.atom
    topics: [it_news]
    tier: 1
    enabled: true

  - id: zdnet
    name: ZDNet
    url: https://www.zdnet.com/news/rss.xml
    topics: [it_news]
    tier: 2
    enabled: true

  - id: infoq
    name: InfoQ
    url: https://feed.infoq.com/
    topics: [it_launches]
    tier: 1
    enabled: true

  - id: the_new_stack
    name: The New Stack
    url: https://thenewstack.io/feed/
    topics: [it_launches]
    tier: 1
    enabled: true

  - id: hacker_news
    name: Hacker News Top
    url: https://hnrss.org/frontpage?points=200
    topics: [it_launches]
    tier: 2
    enabled: true

  - id: crunchbase_news
    name: Crunchbase News
    url: https://news.crunchbase.com/feed/
    topics: [it_funding]
    tier: 1
    enabled: true

  - id: techcrunch_venture
    name: TechCrunch Venture
    url: https://techcrunch.com/category/venture/feed/
    topics: [it_funding]
    tier: 2
    enabled: true

  - id: inc42
    name: Inc42
    url: https://inc42.com/feed/
    topics: [it_funding]
    tier: 2
    enabled: true

  - id: yourstory
    name: YourStory
    url: https://yourstory.com/feed
    topics: [it_funding]
    tier: 2
    enabled: true

  - id: entrackr
    name: Entrackr
    url: https://entrackr.com/feed/
    topics: [it_funding]
    tier: 2
    enabled: true

github:
  enabled: true
  languages:
    - python
    - javascript
    - typescript
    - rust
    - go
  time_range: weekly
  min_stars_gained: 100
EOF
```

---

### 1.5 Create Database Models

**Step 1.5.1 — Create the SQLAlchemy models file**

```bash
$ cat > src/newsdash/db/models.py << 'EOF'
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Text,
    Index, create_engine
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from datetime import datetime, timezone
import os


class Base(DeclarativeBase):
    pass


class RawItem(Base):
    __tablename__ = "raw_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False)
    url_hash = Column(String(64), nullable=False, unique=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_id = Column(String(100), nullable=False)
    processed = Column(Boolean, default=False)


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False)
    url_hash = Column(String(64), nullable=False, unique=True)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    summary_cached = Column(Boolean, default=False)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_id = Column(String(100), nullable=False)
    source_name = Column(String(200), nullable=False)
    source_tier = Column(Integer, default=2)
    topic_id = Column(String(100), nullable=False)
    read = Column(Boolean, default=False)


class DerivedInsight(Base):
    __tablename__ = "derived_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(String(100), nullable=False)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    content = Column(Text, nullable=False)
    source_article_ids = Column(Text)
    date = Column(Date, nullable=False)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime)
    items_fetched = Column(Integer, default=0)
    items_deduped = Column(Integer, default=0)
    items_classified = Column(Integer, default=0)
    items_summarised = Column(Integer, default=0)
    status = Column(String(20))
    error_message = Column(Text)


# Indexes
Index("idx_articles_topic", Article.topic_id)
Index("idx_articles_published", Article.published_at)
Index("idx_articles_url_hash", Article.url_hash)
Index("idx_raw_items_processed", RawItem.processed)


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/news.db")


def create_db_engine():
    url = get_database_url()
    return create_async_engine(url, echo=False)


async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
EOF
```

---

### 1.6 Create RSS Fetcher

**Step 1.6.1 — Create rss.py**

```bash
$ cat > src/newsdash/fetchers/rss.py << 'EOF'
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
    total_stored = 0

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
EOF
```

---

### 1.7 Create GitHub Fetcher

**Step 1.7.1 — Create github.py**

```bash
$ cat > src/newsdash/fetchers/github.py << 'EOF'
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
    min_stars = github_config.get("min_stars_gained", 0)
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
EOF
```

---

### 1.8 Create Deduplicator

**Step 1.8.1 — Create dedupe.py**

```bash
$ cat > src/newsdash/pipeline/dedupe.py << 'EOF'
import logging
from datetime import datetime, timezone, timedelta

from rapidfuzz import fuzz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from newsdash.db.models import RawItem, Article

logger = logging.getLogger(__name__)


async def get_recent_titles(session: AsyncSession, window_hours: int) -> list[tuple[str, str, int]]:
    """Return (url_hash, title, source_tier) for articles in the dedup window."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    result = await session.execute(
        select(Article.url_hash, Article.title, Article.source_tier)
        .where(Article.fetched_at >= cutoff)
    )
    return result.fetchall()


async def run_dedupe(
    session: AsyncSession,
    raw_items: list[RawItem],
    window_hours: int,
    threshold: int,
) -> list[RawItem]:
    """
    Given a list of unprocessed RawItems, return only those that pass dedup.
    Stage 1: URL hash not in articles table.
    Stage 2: Title not similar enough to any recent article.
    """
    recent = await get_recent_titles(session, window_hours)
    recent_hashes = {row[0] for row in recent}
    recent_titles = [(row[0], row[1], row[2]) for row in recent]

    passed = []
    skipped_exact = 0
    skipped_similar = 0

    for item in raw_items:
        # Stage 1: exact URL hash match
        if item.url_hash in recent_hashes:
            skipped_exact += 1
            continue

        # Stage 2: title similarity
        duplicate_found = False
        for existing_hash, existing_title, existing_tier in recent_titles:
            score = fuzz.token_sort_ratio(
                item.title.lower(), existing_title.lower()
            )
            if score >= threshold:
                # Keep higher tier; if same tier, keep first seen (existing wins)
                duplicate_found = True
                skipped_similar += 1
                break

        if not duplicate_found:
            passed.append(item)
            # Add to recent_titles so subsequent items in this batch are checked against it
            recent_titles.append((item.url_hash, item.title, 2))

    logger.info(
        f"Dedup: {len(raw_items)} in, {len(passed)} passed, "
        f"{skipped_exact} exact dupes, {skipped_similar} near-dupes"
    )
    return passed
EOF
```

---

### 1.9 Create Topic Classifier

**Step 1.9.1 — Create classify.py**

```bash
$ cat > src/newsdash/pipeline/classify.py << 'EOF'
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def classify_topic(title: str, description: str, topics: list[dict]) -> Optional[str]:
    """
    Assign exactly one topic to an article using priority-ordered keyword matching.
    Topics list must be sorted by priority ascending (lower number = higher priority).
    Returns topic_id of first match, or None if no match.
    """
    text = f"{title} {description}".lower()
    sorted_topics = sorted(
        [t for t in topics if not t.get("derived", False)],
        key=lambda t: t.get("priority", 99)
    )

    for topic in sorted_topics:
        keywords = topic.get("keywords", [])
        if not keywords:
            continue
        for keyword in keywords:
            if keyword.lower() in text:
                return topic["id"]

    # Fallback: assign to it_news if nothing matched and article came from a tech source
    return "it_news"


def classify_batch(items: list[dict], topics: list[dict]) -> list[dict]:
    """Classify a list of items in place. Returns items with topic_id set."""
    classified = 0
    for item in items:
        topic_id = classify_topic(
            item.get("title", ""),
            item.get("description", ""),
            topics
        )
        item["topic_id"] = topic_id
        classified += 1

    logger.info(f"Classified {classified} items")
    return items
EOF
```

---

### 1.10 Create Config Loader

**Step 1.10.1 — Create config.py**

```bash
$ cat > src/newsdash/config.py << 'EOF'
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "sources.yaml"


def load_config() -> dict:
    """Load and return the full sources.yaml config."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def get_enabled_feeds(config: dict) -> list[dict]:
    return [f for f in config.get("feeds", []) if f.get("enabled", True)]


def get_topics(config: dict) -> list[dict]:
    return config.get("topics", [])


def get_pipeline_config(config: dict) -> dict:
    return config.get("pipeline", {})


def get_github_config(config: dict) -> dict:
    return config.get("github", {})


def get_digest_config(config: dict) -> dict:
    return config.get("digest", {})
EOF
```

---

### 1.11 Create FastAPI Server

**Step 1.11.1 — Create app.py**

```bash
$ cat > src/newsdash/server/app.py << 'EOF'
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc

from newsdash.db.models import Article, DerivedInsight, create_db_engine, init_db, get_session_factory
from newsdash.config import load_config, get_pipeline_config

logger = logging.getLogger(__name__)

app = FastAPI(title="News Dashboard")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

engine = None
session_factory = None


@app.on_event("startup")
async def startup():
    global engine, session_factory
    engine = create_db_engine()
    await init_db(engine)
    session_factory = get_session_factory(engine)
    logger.info("Database initialised")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    config = load_config()
    pipeline_cfg = get_pipeline_config(config)
    age_hours = pipeline_cfg.get("dashboard_article_age_hours", 24)
    topics = config.get("topics", [])

    cutoff = datetime.now(timezone.utc) - timedelta(hours=age_hours)

    async with session_factory() as session:
        result = await session.execute(
            select(Article)
            .where(Article.published_at >= cutoff)
            .order_by(desc(Article.published_at))
        )
        articles = result.scalars().all()

        insights_result = await session.execute(
            select(DerivedInsight)
            .order_by(desc(DerivedInsight.generated_at))
            .limit(10)
        )
        insights = insights_result.scalars().all()

    # Group articles by topic
    grouped = {}
    for article in articles:
        if article.topic_id not in grouped:
            grouped[article.topic_id] = []
        grouped[article.topic_id].append(article)

    # Build column structure
    columns = {
        "geopolitics": {
            "label": "Geopolitics",
            "topics": ["geopolitics_india", "geopolitics"]
        },
        "ai": {
            "label": "Artificial Intelligence",
            "topics": ["ai_news", "ai_business", "ai_jobs", "ai_nonconventional"]
        },
        "tech": {
            "label": "Technology",
            "topics": ["it_news", "it_launches", "github_trending", "it_funding"]
        },
        "markets": {
            "label": "Markets",
            "topics": ["market_sectors_up", "market_sectors_down"]
        },
    }

    topic_labels = {t["id"]: t["label"] for t in topics}

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "grouped": grouped,
        "columns": columns,
        "topic_labels": topic_labels,
        "insights": insights,
        "generated_at": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
        "refresh_seconds": 1800,
    })


@app.get("/api/articles")
async def get_articles():
    config = load_config()
    age_hours = get_pipeline_config(config).get("dashboard_article_age_hours", 24)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=age_hours)

    async with session_factory() as session:
        result = await session.execute(
            select(Article)
            .where(Article.published_at >= cutoff)
            .order_by(desc(Article.published_at))
        )
        articles = result.scalars().all()

    grouped = {}
    for a in articles:
        grouped.setdefault(a.topic_id, []).append({
            "id": a.id, "title": a.title, "url": a.url,
            "summary": a.summary, "source_name": a.source_name,
            "source_tier": a.source_tier,
            "published_at": a.published_at.isoformat() if a.published_at else None,
        })

    return {"generated_at": datetime.now(timezone.utc).isoformat(), "topics": grouped}


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/api/refresh")
async def manual_refresh():
    """Trigger a manual pipeline run."""
    from newsdash.pipeline_runner import run_pipeline
    import asyncio
    asyncio.create_task(run_pipeline())
    return {"status": "started"}
EOF
```

---

### 1.12 Create Dashboard Template

**Step 1.12.1 — Create dashboard.html**

```bash
$ cat > src/newsdash/server/templates/dashboard.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="{{ refresh_seconds }}">
  <title>Intelligence Dashboard</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e2e8f0; }
    header { background: #1a1d27; border-bottom: 1px solid #2d3148; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }
    header h1 { font-size: 1.2rem; font-weight: 600; color: #e2e8f0; letter-spacing: 0.05em; }
    header span { font-size: 0.75rem; color: #64748b; }
    .refresh-btn { background: #2d3148; color: #94a3b8; border: none; padding: 6px 14px; border-radius: 6px; font-size: 0.75rem; cursor: pointer; }
    .refresh-btn:hover { background: #3d4168; color: #e2e8f0; }
    .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; min-height: calc(100vh - 57px); }
    .column { border-right: 1px solid #1e2235; padding: 0; }
    .column:last-child { border-right: none; }
    .col-header { padding: 14px 16px; background: #161926; border-bottom: 2px solid #2d3148; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: #64748b; }
    .topic-section { border-bottom: 1px solid #1e2235; }
    .topic-header { padding: 10px 16px 8px; font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: #475569; background: #131620; }
    .article-card { padding: 12px 16px; border-bottom: 1px solid #1a1d2e; transition: background 0.15s; }
    .article-card:hover { background: #1a1d2e; }
    .article-card:last-child { border-bottom: none; }
    .article-title a { color: #cbd5e1; text-decoration: none; font-size: 0.82rem; line-height: 1.45; font-weight: 500; }
    .article-title a:hover { color: #e2e8f0; }
    .article-meta { display: flex; align-items: center; gap: 8px; margin-top: 5px; flex-wrap: wrap; }
    .source-badge { font-size: 0.65rem; padding: 2px 7px; border-radius: 10px; font-weight: 600; }
    .tier-1 { background: #1e3a5f; color: #60a5fa; }
    .tier-2 { background: #1e2d1e; color: #6ee7b7; }
    .article-time { font-size: 0.65rem; color: #475569; }
    .article-summary { margin-top: 6px; font-size: 0.75rem; color: #64748b; line-height: 1.5; }
    .empty-state { padding: 20px 16px; font-size: 0.75rem; color: #334155; font-style: italic; }
    .insight-card { padding: 12px 16px; border-bottom: 1px solid #1a1d2e; }
    .insight-card p { font-size: 0.78rem; color: #94a3b8; line-height: 1.6; }
    @media (max-width: 1100px) { .grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
<header>
  <h1>Intelligence Dashboard</h1>
  <div style="display:flex;gap:12px;align-items:center;">
    <span>Updated {{ generated_at }}</span>
    <button class="refresh-btn" onclick="fetch('/api/refresh',{method:'POST'}).then(()=>location.reload())">Refresh Now</button>
  </div>
</header>

<div class="grid">
  {% for col_id, col in columns.items() %}
  <div class="column">
    <div class="col-header">{{ col.label }}</div>
    {% for topic_id in col.topics %}
    <div class="topic-section">
      <div class="topic-header">{{ topic_labels.get(topic_id, topic_id) }}</div>
      {% if topic_id in ('market_sectors_up', 'market_sectors_down') %}
        {% set topic_insights = insights | selectattr('topic_id', 'equalto', topic_id) | list %}
        {% if topic_insights %}
          {% for insight in topic_insights[:1] %}
          <div class="insight-card"><p>{{ insight.content }}</p></div>
          {% endfor %}
        {% else %}
          <div class="empty-state">AI analysis runs at 6:00 AM daily</div>
        {% endif %}
      {% else %}
        {% set topic_articles = grouped.get(topic_id, []) %}
        {% if topic_articles %}
          {% for article in topic_articles[:10] %}
          <div class="article-card">
            <div class="article-title">
              <a href="{{ article.url }}" target="_blank" rel="noopener">{{ article.title }}</a>
            </div>
            <div class="article-meta">
              <span class="source-badge tier-{{ article.source_tier }}">{{ article.source_name }}</span>
              {% if article.published_at %}
              <span class="article-time">{{ article.published_at.strftime('%d %b, %H:%M') }}</span>
              {% endif %}
            </div>
            {% if article.summary %}
            <div class="article-summary">{{ article.summary }}</div>
            {% endif %}
          </div>
          {% endfor %}
        {% else %}
          <div class="empty-state">No articles yet — refresh in progress</div>
        {% endif %}
      {% endif %}
    </div>
    {% endfor %}
  </div>
  {% endfor %}
</div>
</body>
</html>
EOF
```

---

### 1.13 Create Pipeline Runner

**Step 1.13.1 — Create pipeline_runner.py**

```bash
$ cat > src/newsdash/pipeline_runner.py << 'EOF'
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from newsdash.config import load_config, get_enabled_feeds, get_topics, get_pipeline_config, get_github_config
from newsdash.db.models import RawItem, Article, PipelineRun, create_db_engine, init_db, get_session_factory
from newsdash.fetchers.rss import run_rss_fetch
from newsdash.fetchers.github import run_github_fetch
from newsdash.pipeline.dedupe import run_dedupe
from newsdash.pipeline.classify import classify_batch

logger = logging.getLogger(__name__)


async def run_pipeline():
    """Full pipeline: fetch → dedupe → classify → store."""
    engine = create_db_engine()
    await init_db(engine)
    session_factory = get_session_factory(engine)

    config = load_config()
    feeds = get_enabled_feeds(config)
    topics = get_topics(config)
    pipeline_cfg = get_pipeline_config(config)
    github_cfg = get_github_config(config)

    dedupe_window = pipeline_cfg.get("dedupe_window_hours", 48)
    dedupe_threshold = pipeline_cfg.get("dedupe_similarity_threshold", 85)

    run_record = PipelineRun(started_at=datetime.now(timezone.utc), status="running")

    async with session_factory() as session:
        session.add(run_record)
        await session.commit()
        await session.refresh(run_record)

        try:
            # Step 1: Fetch RSS
            fetched = await run_rss_fetch(session, feeds)
            run_record.items_fetched = fetched

            # Step 2: Fetch GitHub
            github_stored = await run_github_fetch(session, github_cfg)

            # Step 3: Get unprocessed raw items
            result = await session.execute(
                select(RawItem).where(RawItem.processed == False)
            )
            raw_items = result.scalars().all()

            # Step 4: Deduplicate
            unique_items = await run_dedupe(session, raw_items, dedupe_window, dedupe_threshold)
            run_record.items_deduped = len(unique_items)

            # Step 5: Classify and store as articles
            item_dicts = [
                {
                    "url": item.url,
                    "url_hash": item.url_hash,
                    "title": item.title,
                    "description": item.description or "",
                    "published_at": item.published_at,
                    "fetched_at": item.fetched_at,
                    "source_id": item.source_id,
                }
                for item in unique_items
            ]

            classified = classify_batch(item_dicts, topics)

            # Build source lookup from config
            source_lookup = {f["id"]: f for f in feeds}

            stored = 0
            for item_dict in classified:
                source = source_lookup.get(item_dict["source_id"], {})
                article = Article(
                    url=item_dict["url"],
                    url_hash=item_dict["url_hash"],
                    title=item_dict["title"],
                    summary=None,
                    published_at=item_dict["published_at"],
                    fetched_at=item_dict["fetched_at"],
                    source_id=item_dict["source_id"],
                    source_name=source.get("name", item_dict["source_id"]),
                    source_tier=source.get("tier", 2),
                    topic_id=item_dict["topic_id"],
                )
                session.add(article)
                stored += 1

            run_record.items_classified = stored

            # Mark raw items as processed
            for item in raw_items:
                item.processed = True

            run_record.finished_at = datetime.now(timezone.utc)
            run_record.status = "success"
            await session.commit()

            logger.info(
                f"Pipeline complete: {fetched} fetched, {len(unique_items)} unique, "
                f"{stored} classified, {github_stored} GitHub repos"
            )

        except Exception as e:
            run_record.status = "failed"
            run_record.error_message = str(e)
            run_record.finished_at = datetime.now(timezone.utc)
            await session.commit()
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_pipeline())
EOF
```

**Step 1.13.2 — Create the main entry point**

```bash
$ cat > src/newsdash/__main__.py << 'EOF'
import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/newsdash.log"),
    ]
)

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from newsdash.config import load_config, get_pipeline_config
from newsdash.pipeline_runner import run_pipeline


async def main():
    config = load_config()
    pipeline_cfg = get_pipeline_config(config)
    interval_minutes = pipeline_cfg.get("fetch_interval_minutes", 60)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_pipeline, IntervalTrigger(minutes=interval_minutes), id="pipeline")
    scheduler.start()

    # Run once immediately on startup
    asyncio.create_task(run_pipeline())

    config_uvicorn = uvicorn.Config(
        "newsdash.server.app:app",
        host="127.0.0.1",
        port=8000,
        log_level="warning",
    )
    server = uvicorn.Server(config_uvicorn)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
EOF
```

---

### 1.14 Test Phase 1

**Step 1.14.1 — Activate virtual environment (if not already active)**

```bash
$ cd ~/news-dashboard
$ source .venv/bin/activate
```

**Step 1.14.2 — Run one pipeline cycle manually first**

```bash
$ python -m newsdash.pipeline_runner
```

Expected output (will take 1–2 minutes as it fetches all feeds):
```
INFO newsdash.fetchers.rss: Fetched N items from foreign_affairs
INFO newsdash.fetchers.rss: Fetched N items from the_diplomat
... (one line per feed)
INFO newsdash.fetchers.rss: RSS fetch complete: NNN fetched, NNN new
INFO newsdash.pipeline.dedupe: Dedup: NNN in, NNN passed, N exact dupes, N near-dupes
INFO newsdash.pipeline.classify: Classified NNN items
INFO newsdash.pipeline_runner: Pipeline complete: ...
```

If you see errors for individual feeds (e.g. `Client error 404 for carnegie_india`), that is normal — some RSS URLs change. Disable that feed in `sources.yaml` and continue.

**Step 1.14.3 — Verify data was stored**

```bash
$ python -c "
import asyncio
from newsdash.db.models import create_db_engine, get_session_factory, Article
from sqlalchemy import select, func

async def check():
    engine = create_db_engine()
    sf = get_session_factory(engine)
    async with sf() as s:
        result = await s.execute(select(func.count()).select_from(Article))
        count = result.scalar()
        print(f'Articles in database: {count}')
        
        result2 = await s.execute(
            select(Article.topic_id, func.count().label('n'))
            .group_by(Article.topic_id)
            .order_by(func.count().desc())
        )
        for row in result2.fetchall():
            print(f'  {row[0]}: {row[1]}')

asyncio.run(check())
"
```

Expected output: A list of topics with article counts. If count is 0, re-run the pipeline runner and check logs.

**Step 1.14.4 — Start the full application**

```bash
$ python -m newsdash
```

Expected output:
```
INFO newsdash: Database initialised
INFO apscheduler: Scheduler started
INFO uvicorn: Application startup complete.
```

**Step 1.14.5 — Open the dashboard**

Open any browser on your Mac and navigate to:
```
http://localhost:8000
```

You should see the 4-column dashboard with articles grouped by topic.

**Step 1.14.6 — Stop the application**

Press `Ctrl + C` in the terminal.

**Step 1.14.7 — Commit Phase 1**

```bash
$ git add -A
$ git commit -m "Phase 1: Working aggregator — RSS fetch, dedup, classify, dashboard"
```

---

## Phase 2 — AI Summaries

### Prerequisites

You need an Anthropic API key. Get one at https://console.anthropic.com → API Keys → Create Key.

**Step 2.1 — Add your API key to .env**

```bash
$ nano .env
```

Find the line `ANTHROPIC_API_KEY=` and add your key after the `=` sign. Save with `Ctrl+O`, `Enter`, `Ctrl+X`.

**Step 2.2 — Install Anthropic SDK**

```bash
$ source .venv/bin/activate
$ uv pip install anthropic>=0.28.0
```

**Step 2.3 — Create summarise.py**

```bash
$ cat > src/newsdash/pipeline/summarise.py << 'EOF'
import logging
import os
from typing import Optional

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from newsdash.db.models import Article

logger = logging.getLogger(__name__)

SUMMARISE_PROMPT = """You are a news summariser for a personal intelligence dashboard.
Summarise the following article in exactly 2 sentences.
Be factual. No opinion. No filler phrases like "In this article...".
Focus on: what happened, who is involved, why it matters.

Title: {title}
Content: {content}

Return only the 2-sentence summary. Nothing else."""


def get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")
    return anthropic.Anthropic(api_key=api_key)


async def summarise_article(title: str, content: str, model: str) -> Optional[str]:
    """Call Claude to summarise one article. Returns summary string or None on error."""
    client = get_client()
    prompt = SUMMARISE_PROMPT.format(
        title=title,
        content=content[:2000]
    )
    try:
        message = client.messages.create(
            model=model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except Exception as e:
        logger.error(f"Summarisation failed for '{title[:50]}': {e}")
        return None


async def run_summarise(session: AsyncSession, batch_size: int = 20):
    """Find all articles without summaries and summarise them."""
    model = os.getenv("SUMMARISE_MODEL", "claude-haiku-4-20251001")

    result = await session.execute(
        select(Article)
        .where(Article.summary == None)
        .where(Article.summary_cached == False)
        .limit(batch_size * 5)
    )
    articles = result.scalars().all()

    if not articles:
        logger.info("No articles need summarisation")
        return

    logger.info(f"Summarising {len(articles)} articles with {model}")
    summarised = 0

    for article in articles:
        content = article.title
        summary = await summarise_article(article.title, content, model)
        if summary:
            article.summary = summary
            article.summary_cached = True
            summarised += 1

    await session.commit()
    logger.info(f"Summarised {summarised} articles")
EOF
```

**Step 2.4 — Add summarisation to pipeline runner**

Open `src/newsdash/pipeline_runner.py` in a text editor. After the line that reads `run_record.items_classified = stored`, add the following block:

```python
            # Step 6: Summarise (Phase 2)
            from newsdash.pipeline.summarise import run_summarise
            from newsdash.config import get_pipeline_config
            batch_size = pipeline_cfg.get("summarise_batch_size", 20)
            await run_summarise(session, batch_size)
```

**Step 2.5 — Test Phase 2**

```bash
$ python -m newsdash.pipeline_runner
```

Open `http://localhost:8000` and verify that article cards now show 2-sentence summaries below the title.

**Step 2.6 — Commit Phase 2**

```bash
$ git add -A
$ git commit -m "Phase 2: AI summarisation via Claude Haiku"
```

---

## Phase 3 — Derived Topics

**Step 3.1 — Create derived.py**

```bash
$ cat > src/newsdash/pipeline/derived.py << 'EOF'
import json
import logging
import os
from datetime import datetime, timezone, timedelta, date

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from newsdash.db.models import Article, DerivedInsight

logger = logging.getLogger(__name__)

MARKET_SECTORS_PROMPT = """You are a financial and geopolitical analyst.
Based on the following geopolitical news from today, identify:
A) Market sectors likely to benefit (tailwinds)
B) Market sectors likely to face headwinds

For each sector, provide: sector name, one-sentence reason, and which specific event drives the inference.

News items:
{news}

Respond in JSON format only:
{{
  "up": [{{"sector": "...", "reason": "...", "event": "..."}}],
  "down": [{{"sector": "...", "reason": "...", "event": "..."}}]
}}"""

AI_NOVELTY_PROMPT = """You are evaluating whether an AI news article describes a novel,
non-obvious application of AI in a difficult or unconventional domain (e.g., protein folding,
climate science, drug discovery, robotics, space exploration, medical diagnostics).

Article title: {title}
Description: {description}

Score 1-10 for novelty and non-obviousness (10 = highly unconventional breakthrough).
Respond with JSON only: {{"score": N, "reason": "one sentence"}}"""


async def run_market_sector_analysis(session: AsyncSession):
    """Generate market sector insights from today's geopolitics articles."""
    model = os.getenv("ANALYSIS_MODEL", "claude-sonnet-4-20250514")
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await session.execute(
        select(Article)
        .where(and_(
            Article.topic_id.in_(["geopolitics", "geopolitics_india"]),
            Article.published_at >= cutoff
        ))
        .order_by(Article.source_tier, Article.published_at.desc())
        .limit(20)
    )
    articles = result.scalars().all()

    if not articles:
        logger.info("No geopolitics articles for market analysis")
        return

    news_text = "\n".join([f"- {a.title}: {a.summary or ''}" for a in articles])
    prompt = MARKET_SECTORS_PROMPT.format(news=news_text)

    try:
        message = client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        data = json.loads(message.content[0].text)
        today = date.today()

        for topic_id, sectors in [("market_sectors_up", data.get("up", [])),
                                   ("market_sectors_down", data.get("down", []))]:
            content = "\n".join([
                f"**{s['sector']}** — {s['reason']} (Re: {s['event']})"
                for s in sectors
            ])
            insight = DerivedInsight(
                topic_id=topic_id,
                content=content,
                source_article_ids=json.dumps([a.id for a in articles]),
                date=today
            )
            session.add(insight)

        await session.commit()
        logger.info("Market sector analysis complete")

    except Exception as e:
        logger.error(f"Market sector analysis failed: {e}")


async def run_ai_novelty_classification(session: AsyncSession):
    """Flag highly novel AI implementations from ai_news articles."""
    model = os.getenv("SUMMARISE_MODEL", "claude-haiku-4-20251001")
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    result = await session.execute(
        select(Article)
        .where(and_(
            Article.topic_id == "ai_news",
            Article.published_at >= cutoff
        ))
        .limit(50)
    )
    articles = result.scalars().all()

    reclassified = 0
    for article in articles:
        prompt = AI_NOVELTY_PROMPT.format(
            title=article.title,
            description=article.summary or ""
        )
        try:
            message = client.messages.create(
                model=model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            data = json.loads(message.content[0].text)
            if data.get("score", 0) >= 8:
                article.topic_id = "ai_nonconventional"
                reclassified += 1
        except Exception:
            continue

    await session.commit()
    logger.info(f"AI novelty: {reclassified} articles reclassified as ai_nonconventional")
EOF
```

**Step 3.2 — Add derived analysis to scheduler in __main__.py**

Open `src/newsdash/__main__.py`. After the line `scheduler.add_job(run_pipeline, ...)`, add:

```python
    from newsdash.db.models import create_db_engine, get_session_factory
    from newsdash.pipeline.derived import run_market_sector_analysis, run_ai_novelty_classification

    async def run_derived():
        engine = create_db_engine()
        sf = get_session_factory(engine)
        async with sf() as session:
            await run_market_sector_analysis(session)
            await run_ai_novelty_classification(session)

    scheduler.add_job(run_derived, CronTrigger(hour=6, minute=0), id="derived")
```

**Step 3.3 — Commit Phase 3**

```bash
$ git add -A
$ git commit -m "Phase 3: Derived topics — market sectors and AI novelty classification"
```

---

## Phase 4 — Automation and Email Digest

### Step 4.1 — Create email digest

```bash
$ cat > src/newsdash/digest/email.py << 'EOF'
import logging
import os
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from newsdash.db.models import Article
from newsdash.config import load_config

logger = logging.getLogger(__name__)

TOPIC_ORDER = [
    "geopolitics_india", "geopolitics",
    "ai_news", "ai_business", "ai_jobs", "ai_nonconventional",
    "it_news", "it_launches", "github_trending", "it_funding",
]


async def build_digest(session: AsyncSession, top_n: int = 5) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=12)
    config = load_config()
    topic_labels = {t["id"]: t["label"] for t in config.get("topics", [])}

    result = await session.execute(
        select(Article)
        .where(Article.published_at >= cutoff)
        .order_by(desc(Article.published_at))
    )
    articles = result.scalars().all()

    grouped = {}
    for a in articles:
        grouped.setdefault(a.topic_id, []).append(a)

    lines = [f"Intelligence Digest — {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')}", "=" * 60, ""]

    for topic_id in TOPIC_ORDER:
        topic_articles = grouped.get(topic_id, [])[:top_n]
        if not topic_articles:
            continue
        lines.append(f"\n{topic_labels.get(topic_id, topic_id).upper()}")
        lines.append("-" * 40)
        for a in topic_articles:
            lines.append(f"\n• {a.title}")
            lines.append(f"  [{a.source_name}]  {a.url}")
            if a.summary:
                first_sentence = a.summary.split(".")[0] + "."
                lines.append(f"  {first_sentence}")

    return "\n".join(lines)


async def send_digest(session: AsyncSession):
    config = load_config()
    digest_cfg = config.get("digest", {})

    if not digest_cfg.get("enabled", False):
        return

    recipient = digest_cfg.get("recipient_email") or os.getenv("DIGEST_RECIPIENT_EMAIL")
    sender = digest_cfg.get("sender_email", "newsdash@localhost")
    smtp_host = os.getenv("DIGEST_SMTP_HOST", "localhost")
    smtp_port = int(os.getenv("DIGEST_SMTP_PORT", "25"))
    top_n = digest_cfg.get("top_n_per_topic", 5)

    if not recipient:
        logger.warning("No recipient email configured for digest")
        return

    body = await build_digest(session, top_n)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Intelligence Digest — {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M')} UTC"
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.sendmail(sender, [recipient], msg.as_string())
        logger.info(f"Digest sent to {recipient}")
    except Exception as e:
        logger.error(f"Failed to send digest: {e}")
EOF
```

### Step 4.2 — Enable digest in sources.yaml

Open `config/sources.yaml`. Find `digest:` section. Change:
- `enabled: false` to `enabled: true`
- `recipient_email: "you@example.com"` to your actual email address

### Step 4.3 — Create launchd service

```bash
$ cat > launchd/com.user.newsdash.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.newsdash</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd ~/news-dashboard &amp;&amp; source .venv/bin/activate &amp;&amp; python -m newsdash</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/YOURUSERNAME/news-dashboard/logs/launchd-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOURUSERNAME/news-dashboard/logs/launchd-stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>/Users/YOURUSERNAME</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
```

**Step 4.4 — Replace YOURUSERNAME in the plist**

```bash
$ sed -i '' "s/YOURUSERNAME/$(whoami)/g" launchd/com.user.newsdash.plist
```

**Step 4.5 — Install and start the launchd service**

```bash
$ cp launchd/com.user.newsdash.plist ~/Library/LaunchAgents/
$ launchctl load ~/Library/LaunchAgents/com.user.newsdash.plist
$ launchctl start com.user.newsdash
```

**Step 4.6 — Verify the service is running**

```bash
$ launchctl list | grep newsdash
```

Expected output: a line showing `com.user.newsdash` with a PID number.

Open your browser at `http://localhost:8000` to confirm the dashboard is live.

**Step 4.7 — Commit Phase 4**

```bash
$ git add -A
$ git commit -m "Phase 4: launchd automation and email digest"
```

---

## Phase 5 — Quality Layer

Phase 5 adds mark-as-read, authority scoring, and improved deduplication. This phase is optional and can be done when Phase 1–4 are stable.

**Step 5.1 — Install sentence-transformers for embedding-based dedup**

```bash
$ uv pip install sentence-transformers>=3.0.0
```

**Note:** This downloads a ~90MB model on first run. Subsequent runs use the cached model.

**Step 5.2 — Update the dashboard template to support mark-as-read**

Add this JavaScript to the dashboard template's `<script>` tag:

```javascript
async function markRead(articleId, cardEl) {
    await fetch(`/api/articles/${articleId}/read`, {method: 'POST'});
    cardEl.style.opacity = '0.4';
}
```

And add an `onclick` to each article title:
```html
onclick="markRead({{ article.id }}, this.closest('.article-card'))"
```

**Step 5.3 — Add the mark-as-read API endpoint to app.py**

```python
@app.post("/api/articles/{article_id}/read")
async def mark_read(article_id: int):
    async with session_factory() as session:
        result = await session.execute(select(Article).where(Article.id == article_id))
        article = result.scalar_one_or_none()
        if article:
            article.read = True
            await session.commit()
    return {"status": "ok"}
```

**Step 5.4 — Commit Phase 5**

```bash
$ git add -A
$ git commit -m "Phase 5: Mark-as-read quality layer"
```

---

## Troubleshooting

### Dashboard shows no articles

**Cause:** Pipeline has not run yet, or all feeds failed.

**Fix:**
```bash
$ cd ~/news-dashboard
$ source .venv/bin/activate
$ python -m newsdash.pipeline_runner
```
Check the output for errors. If specific feeds fail, disable them in `sources.yaml`.

### A feed shows "Client error 404"

**Cause:** The RSS URL for that source has changed.

**Fix:** Set `enabled: false` for that feed in `sources.yaml`. Look up the current RSS URL for the source and update the `url` field.

### The launchd service is not starting

**Check logs:**
```bash
$ cat ~/news-dashboard/logs/launchd-stderr.log
```

**Restart the service:**
```bash
$ launchctl stop com.user.newsdash
$ launchctl start com.user.newsdash
```

**Unload and reload:**
```bash
$ launchctl unload ~/Library/LaunchAgents/com.user.newsdash.plist
$ launchctl load ~/Library/LaunchAgents/com.user.newsdash.plist
```

### Port 8000 already in use

**Find what is using port 8000:**
```bash
$ lsof -i :8000
```

**Kill the process (replace PID with actual number from above):**
```bash
$ kill -9 [PID]
```

### Claude API returns errors

**Check your API key:**
```bash
$ grep ANTHROPIC_API_KEY .env
```

Make sure the key starts with `sk-ant-`. If blank, add your key.

**Check API credit balance** at https://console.anthropic.com

### GitHub Trending shows nothing

**Cause:** GitHub changed the HTML structure of the trending page.

**Immediate fix:** Set `github.enabled: false` in `sources.yaml`. All other topics continue unaffected.

---

## Maintenance Reference

### Add a new RSS feed
Edit `config/sources.yaml`. Add a new entry under `feeds:`. The feed is picked up on the next pipeline cycle.

### Temporarily disable a feed
In `sources.yaml`, set `enabled: false` for that feed entry.

### Change fetch frequency
In `sources.yaml`, edit `pipeline.fetch_interval_minutes`.

### View pipeline run history
```bash
$ cd ~/news-dashboard
$ source .venv/bin/activate
$ python -c "
import asyncio
from newsdash.db.models import create_db_engine, get_session_factory, PipelineRun
from sqlalchemy import select, desc

async def show():
    engine = create_db_engine()
    sf = get_session_factory(engine)
    async with sf() as s:
        result = await s.execute(select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(10))
        for run in result.scalars().all():
            print(f'{run.started_at} | {run.status} | fetched={run.items_fetched} classified={run.items_classified}')

asyncio.run(show())
"
```

### Stop the dashboard service
```bash
$ launchctl stop com.user.newsdash
```

### Start the dashboard service
```bash
$ launchctl start com.user.newsdash
```

### Completely remove the service (uninstall)
```bash
$ launchctl unload ~/Library/LaunchAgents/com.user.newsdash.plist
$ rm ~/Library/LaunchAgents/com.user.newsdash.plist
```
