# Technical Document
# Personal Geopolitics & Tech Intelligence Dashboard
**Version:** 1.0  
**Status:** Approved for Build  
**Last Updated:** May 2026  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [Component Specifications](#5-component-specifications)
6. [Database Schema](#6-database-schema)
7. [Configuration System](#7-configuration-system)
8. [Data Pipeline](#8-data-pipeline)
9. [API Specification](#9-api-specification)
10. [Scheduler & Automation](#10-scheduler--automation)
11. [Topic Classification System](#11-topic-classification-system)
12. [LLM Integration](#12-llm-integration)
13. [Build Phases](#13-build-phases)
14. [Non-Functional Requirements](#14-non-functional-requirements)
15. [Security Considerations](#15-security-considerations)

---

## 1. Project Overview

### 1.1 Purpose

A locally-hosted, single-user intelligence dashboard running on macOS. It aggregates news and structured data from authoritative sources across 12 topic areas, de-duplicates content, assigns each article to exactly one topic, summarises using an LLM, and presents everything in a single-page browser dashboard. It also sends a daily email digest.

### 1.2 Core Design Principles

- **Config-driven, not code-driven.** All news sources, topics, and scheduling parameters live in a human-readable YAML file. No Python changes needed to add or remove a source.
- **One article, one topic.** Each ingested article is assigned to exactly one topic using a priority-ordered classifier. No article appears in multiple sections.
- **Derived topics are AI-generated, not fetched.** Topics 3, 4, and 8 (market sector winners/losers, unconventional AI implementations) are produced by a second LLM pass over upstream topic data — not from any RSS feed.
- **Cache everything.** Articles are never re-summarised if already processed. LLM calls are expensive; deduplication happens before summarisation.
- **Phased delivery.** The system is designed in 5 phases. Phase 1 produces a working product. Each subsequent phase adds capability without breaking prior work.

### 1.3 Scope Boundaries

| In Scope | Out of Scope |
|----------|--------------|
| RSS and Atom feed ingestion | Email-to-feed pipeline (newsletters without RSS) |
| GitHub Trending scraping | Social media ingestion (Twitter/X, Reddit) |
| LLM-based summarisation | Full-text article scraping behind paywalls |
| Single-page localhost dashboard | Multi-user access or authentication |
| Daily email digest | Mobile app |
| macOS launchd automation | Cloud hosting or deployment |
| YAML-based source configuration | Admin UI for source management (Phase 5+) |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        macOS Host                           │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Fetchers    │───▶│  Pipeline    │───▶│  SQLite DB   │  │
│  │              │    │              │    │              │  │
│  │ • RSS/Atom   │    │ • Dedupe     │    │ • articles   │  │
│  │ • GitHub     │    │ • Classify   │    │ • summaries  │  │
│  │   Trending   │    │ • Summarise  │    │ • sources    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│          ▲                                       │          │
│          │                                       ▼          │
│  ┌──────────────┐                     ┌──────────────────┐  │
│  │  Scheduler   │                     │  FastAPI Server  │  │
│  │  (launchd /  │                     │  + Jinja2 HTML   │  │
│  │  APScheduler)│                     │  localhost:8000  │  │
│  └──────────────┘                     └──────────────────┘  │
│          │                                       │          │
│          ▼                                       ▼          │
│  ┌──────────────┐                     ┌──────────────────┐  │
│  │  Email       │                     │  Browser         │  │
│  │  Digest      │                     │  Dashboard       │  │
│  │  (8AM/8PM)   │                     │  (auto-refresh)  │  │
│  └──────────────┘                     └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼────────┐
                    │  External APIs   │
                    │  • Claude API    │
                    │  • RSS Feeds     │
                    │  • GitHub.com    │
                    └──────────────────┘
```

### 2.2 Data Flow

```
RSS Feeds / GitHub
        │
        ▼
   [Fetch Layer]          — httpx async, feedparser
        │
        ▼
   [Raw Storage]          — SQLite: raw_items table
        │
        ▼
   [Deduplicate]          — URL hash + title similarity (rapidfuzz)
        │
        ▼
   [Classify Topic]       — Priority-ordered keyword + pattern matcher
        │
        ▼
   [Summarise]            — Claude Haiku / GPT-4o-mini API call
        │                   Cached by URL hash — never re-calls for same article
        ▼
   [articles table]       — Final clean record with topic + summary
        │
        ├──────────────▶  FastAPI → Dashboard (browser)
        │
        └──────────────▶  Digest mailer (8AM + 8PM)
```

### 2.3 Derived Topic Flow (Topics 3, 4, 8)

```
articles WHERE topic IN ('geopolitics', 'geopolitics_india')
        │
        ▼
   [Daily LLM Pass]       — Prompt: "Given these events, which market sectors
        │                    benefit and which face headwinds? Cite event."
        ▼
   derived_insights table
        │
        ▼
   Dashboard sections: market_sectors_up, market_sectors_down

articles WHERE topic = 'ai_news'
        │
        ▼
   [Daily LLM Pass]       — Prompt: "Is this a novel, non-obvious AI
        │                    implementation? Score 1-10. Justify."
        ▼
   articles flagged as ai_nonconventional
```

---

## 3. Technology Stack

### 3.1 Runtime

| Component | Technology | Version | Justification |
|-----------|------------|---------|---------------|
| Language | Python | 3.11+ | Mature async, strong RSS/HTTP ecosystem |
| Web Framework | FastAPI | 0.110+ | Async-native, auto-docs, future JSON API ready |
| Templating | Jinja2 | 3.1+ | Bundled with FastAPI, sufficient for dashboard |
| Database | SQLite | 3.x (stdlib) | Zero-ops, single-file, personal scale |
| ORM | SQLAlchemy | 2.0+ | Async support, clean model definitions |
| HTTP Client | httpx | 0.27+ | Async, modern, replaces requests |
| Feed Parser | feedparser | 6.0+ | Industry standard RSS/Atom parser |
| Fuzzy Match | rapidfuzz | 3.x | Fast C++ backed string similarity for dedup |
| Scheduler | APScheduler | 3.10+ | In-process scheduling, cron-like triggers |
| Config | PyYAML | 6.x | Human-readable, git-trackable source config |
| Email | smtplib | stdlib | No external dependency for digest sending |

### 3.2 LLM APIs (Phase 2+)

| Provider | Model | Use Case | Approx Cost |
|----------|-------|----------|-------------|
| Anthropic | claude-haiku-4 | Article summarisation | ~$0.25 per 1M input tokens |
| Anthropic | claude-sonnet-4 | Derived topic analysis (topics 3,4,8) | ~$3 per 1M input tokens |
| OpenAI (fallback) | gpt-4o-mini | If Anthropic API unavailable | ~$0.15 per 1M input tokens |

### 3.3 Development Tools

| Tool | Purpose |
|------|---------|
| uv | Python package manager (faster than pip) |
| pytest | Testing |
| ruff | Linting and formatting |
| pre-commit | Git hooks for code quality |

---

## 4. Project Structure

```
news-dashboard/
│
├── pyproject.toml              # Project metadata, dependencies
├── .env                        # API keys, email credentials (never committed)
├── .env.example                # Template for .env — committed to git
├── .gitignore
├── README.md
│
├── config/
│   └── sources.yaml            # All feed sources, topic definitions, GitHub config
│
├── src/
│   └── newsdash/
│       ├── __init__.py
│       │
│       ├── fetchers/
│       │   ├── __init__.py
│       │   ├── rss.py          # Async RSS/Atom feed fetcher
│       │   └── github.py       # GitHub Trending scraper
│       │
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── dedupe.py       # URL hash + title similarity deduplication
│       │   ├── classify.py     # Topic assignment (priority-ordered)
│       │   └── summarise.py    # LLM summarisation with cache
│       │
│       ├── db/
│       │   ├── __init__.py
│       │   ├── schema.sql      # Raw DDL for reference
│       │   └── models.py       # SQLAlchemy models
│       │
│       ├── server/
│       │   ├── __init__.py
│       │   ├── app.py          # FastAPI application
│       │   └── templates/
│       │       └── dashboard.html   # Single-page Jinja2 template
│       │
│       ├── digest/
│       │   └── email.py        # Daily digest generator and mailer
│       │
│       ├── config.py           # Config loader — reads sources.yaml
│       └── scheduler.py        # APScheduler setup
│
├── data/
│   └── news.db                 # SQLite database (gitignored)
│
├── logs/
│   └── newsdash.log            # Rotating log file
│
├── launchd/
│   └── com.user.newsdash.plist # macOS launchd service definition
│
└── tests/
    ├── test_rss.py
    ├── test_dedupe.py
    ├── test_classify.py
    └── test_summarise.py
```

---

## 5. Component Specifications

### 5.1 RSS Fetcher (`fetchers/rss.py`)

**Responsibilities:**
- Load all enabled feeds from `sources.yaml`
- Fetch each feed asynchronously using `httpx`
- Parse with `feedparser`
- Extract: `url`, `title`, `description`, `published_at`, `source_id`
- Write raw items to `raw_items` table
- Respect `enabled: false` flags — skip disabled sources
- Handle HTTP errors gracefully — log and continue, never crash the run

**Concurrency model:** `asyncio.gather` with a semaphore limiting to 10 concurrent requests. Prevents rate-limiting from aggressive fetching.

**Retry policy:** 2 retries with 5-second exponential backoff on timeout or 5xx errors. On 4xx: log and skip — do not retry.

### 5.2 GitHub Fetcher (`fetchers/github.py`)

**Responsibilities:**
- Scrape `https://github.com/trending` with filters from `sources.yaml`
- Extract: repo name, description, URL, stars today, total stars, language, topic = `github_trending`
- Write to `raw_items` table in same schema as RSS items

**Note:** GitHub Trending has no official API. Use `httpx` + `BeautifulSoup4` to parse the HTML. The page structure is stable and has been scraped reliably for years. If it breaks, the `enabled` flag in config turns it off instantly.

### 5.3 Deduplicator (`pipeline/dedupe.py`)

**Two-stage deduplication:**

Stage 1 — Exact URL match:
- Compute `SHA256(canonical_url)` where canonical URL strips UTM parameters and trailing slashes
- If hash exists in `articles` table, discard

Stage 2 — Title similarity:
- For items passing Stage 1, compare title against all titles published in the last 48 hours
- Use `rapidfuzz.fuzz.token_sort_ratio`
- Threshold: 85. If score ≥ 85, keep the version with the higher-tier source and discard the other
- This collapses "Reuters reports X" and "Bloomberg: X confirmed" into one card

### 5.4 Topic Classifier (`pipeline/classify.py`)

**Method:** Keyword and pattern matching with a priority-ordered topic list.

**Priority order (highest to lowest):**
```
1. geopolitics_india      — if India/South Asia keywords present
2. geopolitics            — if global geopolitics keywords present
3. it_funding             — if funding/acquisition/M&A keywords present
4. ai_nonconventional     — second-pass LLM flag (Phase 3)
5. ai_jobs                — if job/employment/labor keywords present
6. ai_business            — if enterprise/corporate AI keywords present
7. ai_news                — if AI/ML/LLM/model keywords present
8. github_trending        — all GitHub fetcher items
9. it_launches            — if launch/release/update keywords present
10. it_news               — default IT fallback
11. market_sectors_up     — derived only, never from classifier
12. market_sectors_down   — derived only, never from classifier
```

**Classification logic:** Walk the priority list top-to-bottom. First match wins. Each topic has a keyword set defined in `sources.yaml` under the topic definition. This makes keyword tuning config-only — no code changes.

### 5.5 Summariser (`pipeline/summarise.py`)

**Input:** Article title + description/body (max 2000 chars)  
**Output:** 2-sentence plain English summary  
**Cache key:** `SHA256(url)` — stored in `articles.summary_cached = true`  
**Batch size:** 20 articles per LLM call (reduces API round trips)  
**Model:** Claude Haiku (Phase 2), upgradeable via `.env`

**Prompt template:**
```
You are a news summariser for a personal intelligence dashboard.
Summarise the following article in exactly 2 sentences.
Be factual. No opinion. No filler phrases like "In this article...".
Focus on: what happened, who is involved, why it matters.

Title: {title}
Content: {content}

Return only the 2-sentence summary. Nothing else.
```

### 5.6 FastAPI Server (`server/app.py`)

**Routes:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Main dashboard — renders `dashboard.html` |
| GET | `/api/articles` | JSON: all articles, last 24h, grouped by topic |
| GET | `/api/articles/{topic_id}` | JSON: articles for one topic |
| GET | `/api/insights` | JSON: derived insights (topics 3,4,8) |
| POST | `/api/refresh` | Trigger manual pipeline run |
| GET | `/health` | Health check — returns DB status |

**Dashboard auto-refresh:** The Jinja2 template includes a `<meta http-equiv="refresh" content="1800">` tag — refreshes every 30 minutes automatically.

### 5.7 Email Digest (`digest/email.py`)

**Schedule:** 8:00 AM and 8:00 PM daily (configurable in `sources.yaml`)  
**Format:** Plain text + HTML multipart  
**Structure:** One section per topic column (Geopolitics / AI / Tech & Markets), top 5 articles each, headline + 1-sentence summary + source link  
**Transport:** Local SMTP (macOS Mail) or Resend free tier (100 emails/day free)

---

## 6. Database Schema

```sql
-- Raw items from fetchers before processing
CREATE TABLE raw_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    url             TEXT NOT NULL,
    url_hash        TEXT NOT NULL,           -- SHA256 of canonical URL
    title           TEXT NOT NULL,
    description     TEXT,
    published_at    DATETIME,
    fetched_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_id       TEXT NOT NULL,           -- matches sources.yaml feed id
    processed       BOOLEAN DEFAULT FALSE,
    UNIQUE(url_hash)
);

-- Processed, classified, summarised articles
CREATE TABLE articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    url             TEXT NOT NULL,
    url_hash        TEXT NOT NULL,
    title           TEXT NOT NULL,
    summary         TEXT,                    -- LLM-generated 2-sentence summary
    summary_cached  BOOLEAN DEFAULT FALSE,
    published_at    DATETIME,
    fetched_at      DATETIME,
    source_id       TEXT NOT NULL,
    source_name     TEXT NOT NULL,
    source_tier     INTEGER,                 -- 1 or 2
    topic_id        TEXT NOT NULL,           -- matches topics registry in sources.yaml
    read            BOOLEAN DEFAULT FALSE,   -- for "mark as read" feature (Phase 5)
    UNIQUE(url_hash)
);

-- AI-generated derived insights (topics 3, 4, 8)
CREATE TABLE derived_insights (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id        TEXT NOT NULL,           -- market_sectors_up / market_sectors_down / ai_nonconventional
    generated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    content         TEXT NOT NULL,           -- LLM output
    source_article_ids TEXT,                 -- JSON array of article IDs used as input
    date            DATE NOT NULL            -- one record per topic per day
);

-- Pipeline run log
CREATE TABLE pipeline_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at     DATETIME,
    items_fetched   INTEGER DEFAULT 0,
    items_deduped   INTEGER DEFAULT 0,
    items_classified INTEGER DEFAULT 0,
    items_summarised INTEGER DEFAULT 0,
    status          TEXT,                    -- 'success' | 'partial' | 'failed'
    error_message   TEXT
);

-- Indexes
CREATE INDEX idx_articles_topic     ON articles(topic_id);
CREATE INDEX idx_articles_published ON articles(published_at DESC);
CREATE INDEX idx_articles_url_hash  ON articles(url_hash);
CREATE INDEX idx_raw_items_processed ON raw_items(processed);
```

---

## 7. Configuration System

### 7.1 `sources.yaml` Full Structure

```yaml
# ─────────────────────────────────────────────
# PIPELINE SETTINGS
# ─────────────────────────────────────────────
pipeline:
  fetch_interval_minutes: 60        # How often to run the full fetch cycle
  dedupe_window_hours: 48           # Look-back window for title similarity check
  dedupe_similarity_threshold: 85   # rapidfuzz score threshold (0-100)
  summarise_batch_size: 20          # Articles per LLM API call
  article_retention_days: 30        # Delete articles older than this
  dashboard_article_age_hours: 24   # Only show articles newer than this on dashboard

# ─────────────────────────────────────────────
# DIGEST SETTINGS
# ─────────────────────────────────────────────
digest:
  enabled: true
  schedule:
    - "08:00"
    - "20:00"
  top_n_per_topic: 5                # Articles per topic section in digest
  recipient_email: "you@example.com"
  sender_email: "newsdash@localhost"

# ─────────────────────────────────────────────
# TOPICS REGISTRY
# ─────────────────────────────────────────────
topics:
  - id: geopolitics
    label: "Global Geopolitics"
    dashboard_column: geopolitics
    derived: false
    priority: 2
    keywords:
      - war, conflict, sanctions, treaty, diplomacy, NATO, UN, G20
      - China, Russia, USA, Europe, Middle East, Ukraine, Taiwan
      - trade war, tariffs, alliance, military, nuclear

  - id: geopolitics_india
    label: "Geopolitics — India Impact"
    dashboard_column: geopolitics
    derived: false
    priority: 1
    keywords:
      - India, Modi, Delhi, New Delhi, South Asia, SAARC
      - Pakistan, Bangladesh, Sri Lanka, Nepal, China border
      - Indo-Pacific, Quad, BRICS India, Indian foreign policy

  - id: market_sectors_up
    label: "Sectors to Watch — Tailwinds"
    dashboard_column: markets
    derived: true
    priority: 99

  - id: market_sectors_down
    label: "Sectors Under Pressure"
    dashboard_column: markets
    derived: true
    priority: 99

  - id: ai_news
    label: "AI Space News"
    dashboard_column: ai
    derived: false
    priority: 7
    keywords:
      - artificial intelligence, machine learning, deep learning
      - LLM, large language model, GPT, Claude, Gemini, Llama
      - neural network, transformer, foundation model, AI model

  - id: ai_business
    label: "AI Impact on Business"
    dashboard_column: ai
    derived: false
    priority: 6
    keywords:
      - enterprise AI, AI adoption, AI ROI, AI implementation
      - automation, AI strategy, AI transformation, corporate AI

  - id: ai_jobs
    label: "AI & Job Market"
    dashboard_column: ai
    derived: false
    priority: 5
    keywords:
      - AI jobs, automation displacement, future of work
      - job loss, AI unemployment, workforce, labor market, reskilling

  - id: ai_nonconventional
    label: "Unconventional AI Implementations"
    dashboard_column: ai
    derived: true
    priority: 4

  - id: it_news
    label: "IT Industry News"
    dashboard_column: tech
    derived: false
    priority: 10
    keywords:
      - software, hardware, cloud, cybersecurity, enterprise tech
      - data center, semiconductor, chip, IT infrastructure

  - id: it_launches
    label: "Big Launches & Updates"
    dashboard_column: tech
    derived: false
    priority: 9
    keywords:
      - launch, release, update, version, new feature, announced
      - Product Hunt, changelog, generally available, GA, beta

  - id: github_trending
    label: "Trending on GitHub"
    dashboard_column: tech
    derived: false
    priority: 8

  - id: it_funding
    label: "Funding, M&A & Investments"
    dashboard_column: tech
    derived: false
    priority: 3
    keywords:
      - funding, Series A, Series B, Series C, seed round
      - acquisition, merger, acqui-hire, IPO, valuation, unicorn
      - venture capital, VC, investment round, raises

# ─────────────────────────────────────────────
# FEEDS
# ─────────────────────────────────────────────
feeds:

  # --- GEOPOLITICS (Global) ---
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
    topics: [geopolitics, geopolitics_india]
    tier: 2
    enabled: true

  - id: csis
    name: CSIS — Center for Strategic and International Studies
    url: https://www.csis.org/rss.xml
    topics: [geopolitics]
    tier: 1
    enabled: true

  - id: geopolitical_futures
    name: Geopolitical Futures
    url: https://geopoliticalfutures.com/feed/
    topics: [geopolitics]
    tier: 1
    enabled: true

  - id: bloomberg_world
    name: Bloomberg — World
    url: https://feeds.bloomberg.com/politics/news.rss
    topics: [geopolitics]
    tier: 2
    enabled: true

  - id: reuters_world
    name: Reuters — World
    url: https://feeds.reuters.com/reuters/worldNews
    topics: [geopolitics]
    tier: 2
    enabled: true

  - id: economist_world
    name: The Economist — World
    url: https://www.economist.com/the-world-this-week/rss.xml
    topics: [geopolitics]
    tier: 1
    enabled: true

  # --- GEOPOLITICS (India) ---
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

  - id: the_hindu_international
    name: The Hindu — International
    url: https://www.thehindu.com/news/international/feeder/default.rss
    topics: [geopolitics_india]
    tier: 2
    enabled: true

  - id: the_print_national_security
    name: The Print — National Security
    url: https://theprint.in/category/national-security/feed/
    topics: [geopolitics_india]
    tier: 2
    enabled: true

  - id: indian_express_explained
    name: Indian Express — Explained
    url: https://indianexpress.com/section/explained/feed/
    topics: [geopolitics_india]
    tier: 2
    enabled: true

  # --- AI NEWS ---
  - id: mit_tech_review_ai
    name: MIT Technology Review — AI
    url: https://www.technologyreview.com/topic/artificial-intelligence/feed
    topics: [ai_news]
    tier: 1
    enabled: true

  - id: arxiv_ai
    name: arXiv — cs.AI
    url: https://arxiv.org/rss/cs.AI
    topics: [ai_news]
    tier: 1
    note: "High volume. Phase 2: filter by title keywords to reduce noise."
    enabled: true

  - id: import_ai
    name: Import AI — Jack Clark
    url: https://importai.substack.com/feed
    topics: [ai_news]
    tier: 1
    enabled: true

  - id: the_batch
    name: The Batch — DeepLearning.AI
    url: https://www.deeplearning.ai/the-batch/feed.rss
    topics: [ai_news]
    tier: 1
    enabled: true

  - id: anthropic_blog
    name: Anthropic Research Blog
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
    topics: [ai_news, ai_nonconventional]
    tier: 1
    enabled: true

  - id: meta_ai_blog
    name: Meta AI Blog
    url: https://ai.meta.com/blog/rss/
    topics: [ai_news]
    tier: 1
    enabled: true

  - id: venturebeat_ai
    name: VentureBeat — AI
    url: https://venturebeat.com/category/ai/feed/
    topics: [ai_news]
    tier: 2
    enabled: true

  - id: nature_machine_intelligence
    name: Nature Machine Intelligence
    url: https://www.nature.com/natmachintell.rss
    topics: [ai_news]
    tier: 1
    note: "Abstracts free; full articles paywalled. Abstracts are high signal."
    enabled: true

  # --- AI BUSINESS ---
  - id: hbr_ai
    name: Harvard Business Review — AI
    url: https://hbr.org/topic/subject/ai/rss
    topics: [ai_business]
    tier: 1
    enabled: true

  - id: mckinsey_ai
    name: McKinsey — AI Insights
    url: https://www.mckinsey.com/capabilities/quantumblack/our-insights/rss
    topics: [ai_business]
    tier: 1
    enabled: true

  - id: bcg_ai
    name: BCG — AI & Digital
    url: https://www.bcg.com/rss/ideas.xml
    topics: [ai_business]
    tier: 1
    enabled: true

  - id: gartner_blog
    name: Gartner — Smarter with Gartner
    url: https://www.gartner.com/en/rss/thegartner-blog
    topics: [ai_business]
    tier: 1
    note: "Free tier only. Full reports are paywalled."
    enabled: true

  - id: ai_business_site
    name: AI Business
    url: https://aibusiness.com/rss.xml
    topics: [ai_business]
    tier: 2
    enabled: true

  # --- AI JOBS ---
  - id: stanford_hai
    name: Stanford HAI — News
    url: https://hai.stanford.edu/news/rss.xml
    topics: [ai_jobs]
    tier: 1
    enabled: true

  - id: wef_future_of_work
    name: World Economic Forum — Future of Work
    url: https://www.weforum.org/agenda/tag/future-of-work/rss
    topics: [ai_jobs]
    tier: 1
    enabled: true

  - id: brookings_ai
    name: Brookings Institution — AI
    url: https://www.brookings.edu/topic/artificial-intelligence/feed/
    topics: [ai_jobs]
    tier: 1
    enabled: true

  - id: wired_ai
    name: Wired — AI
    url: https://www.wired.com/feed/tag/ai/rss
    topics: [ai_jobs]
    tier: 2
    enabled: true

  # --- AI NON-CONVENTIONAL (Phase 3 — derived) ---
  - id: ieee_spectrum_ai
    name: IEEE Spectrum — AI
    url: https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss
    topics: [ai_nonconventional]
    tier: 1
    enabled: true

  - id: towards_data_science
    name: Towards Data Science
    url: https://towardsdatascience.com/feed
    topics: [ai_nonconventional]
    tier: 2
    note: "Community posts. Phase 2: filter for editor-picked tag."
    enabled: true

  - id: jmlr
    name: Journal of Machine Learning Research
    url: https://jmlr.org/jmlr.xml
    topics: [ai_nonconventional]
    tier: 1
    enabled: true

  # --- IT NEWS ---
  - id: ars_technica
    name: Ars Technica
    url: https://feeds.arstechnica.com/arstechnica/index
    topics: [it_news]
    tier: 1
    enabled: true

  - id: ieee_spectrum_it
    name: IEEE Spectrum — Tech
    url: https://spectrum.ieee.org/feeds/feed.rss
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

  # --- BIG LAUNCHES & UPDATES ---
  - id: infoq
    name: InfoQ
    url: https://feed.infoq.com/
    topics: [it_launches]
    tier: 1
    enabled: true

  - id: oreilly_radar
    name: O'Reilly Radar
    url: https://www.oreilly.com/radar/feed/index.xml
    topics: [it_launches]
    tier: 1
    enabled: true

  - id: the_new_stack
    name: The New Stack
    url: https://thenewstack.io/feed/
    topics: [it_launches]
    tier: 1
    enabled: true

  - id: hacker_news_top
    name: Hacker News — Top
    url: https://hnrss.org/frontpage?points=200
    topics: [it_launches]
    tier: 2
    note: "Filtered to posts with 200+ points to reduce noise."
    enabled: true

  - id: product_hunt_daily
    name: Product Hunt — Daily
    url: https://www.producthunt.com/feed
    topics: [it_launches]
    tier: 2
    enabled: true

  # --- FUNDING, M&A, INVESTMENTS ---
  - id: crunchbase_news
    name: Crunchbase News
    url: https://news.crunchbase.com/feed/
    topics: [it_funding]
    tier: 1
    enabled: true

  - id: techcrunch_venture
    name: TechCrunch — Venture
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

  - id: venturebeat_funding
    name: VentureBeat — Business
    url: https://venturebeat.com/category/business/feed/
    topics: [it_funding]
    tier: 2
    enabled: true

# ─────────────────────────────────────────────
# GITHUB TRENDING
# ─────────────────────────────────────────────
github:
  enabled: true
  languages:
    - python
    - javascript
    - typescript
    - rust
    - go
    - cpp
  time_range: weekly          # daily | weekly | monthly
  min_stars_gained: 100

# ─────────────────────────────────────────────
# QUARTERLY REPORTS (manual reference — not automated)
# ─────────────────────────────────────────────
reports:
  - name: Stanford AI Index Report
    url: https://aiindex.stanford.edu/report/
    cadence: annual
    topics: [ai_jobs, ai_news]

  - name: McKinsey State of AI
    url: https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai
    cadence: annual
    topics: [ai_business, ai_jobs]

  - name: WEF Future of Jobs Report
    url: https://www.weforum.org/reports/
    cadence: annual
    topics: [ai_jobs]

  - name: JP Morgan AI Research
    url: https://www.jpmorgan.com/insights/research/artificial-intelligence
    cadence: quarterly
    topics: [ai_jobs, ai_business]
```

---

## 8. Data Pipeline

### 8.1 Phase 1 Pipeline (No LLM)

```
Every 60 minutes:
1. Load sources.yaml → get all enabled feeds
2. Async fetch all RSS feeds (max 10 concurrent)
3. For each item: compute url_hash, write to raw_items if not exists
4. For each unprocessed raw_item:
   a. Deduplicate (Stage 1: URL hash, Stage 2: title similarity)
   b. Classify to one topic (priority-ordered keyword match)
   c. Write to articles table (no summary yet)
5. Scrape GitHub Trending → write to articles as github_trending topic
6. Log pipeline run stats to pipeline_runs table
```

### 8.2 Phase 2 Pipeline (With LLM Summarisation)

```
After classification step, before writing to articles:
4c. For each classified item WHERE summary IS NULL:
    - Batch into groups of 20
    - Call Claude Haiku API with batch prompt
    - Write summary back to articles table
    - Set summary_cached = TRUE
```

### 8.3 Phase 3 Pipeline (Derived Topics)

```
Once daily (run at 06:00 AM):
1. SELECT top 20 articles FROM articles
   WHERE topic_id IN ('geopolitics', 'geopolitics_india')
   AND published_at > NOW() - 24 hours
   ORDER BY source_tier ASC, published_at DESC

2. Send to Claude Sonnet with structured prompt:
   "Given these geopolitical events, identify:
    A) Market sectors likely to benefit (with reasoning and source event)
    B) Market sectors likely to face headwinds (with reasoning and source event)
    Format as JSON: {up: [{sector, reason, source_event}], down: [...]}"

3. Write to derived_insights table
   topic_id = 'market_sectors_up' and 'market_sectors_down'

4. Similarly: SELECT ai_news articles → classify ai_nonconventional
```

---

## 9. API Specification

### GET `/`
Returns the full dashboard HTML page. Queries all articles from last 24 hours, grouped by topic, sorted by published_at DESC within each group.

### GET `/api/articles`
```json
{
  "generated_at": "2026-05-24T08:00:00Z",
  "topics": {
    "geopolitics": [
      {
        "id": 1,
        "title": "Article title",
        "summary": "Two sentence summary.",
        "url": "https://...",
        "source_name": "Foreign Affairs",
        "source_tier": 1,
        "published_at": "2026-05-24T06:30:00Z"
      }
    ]
  }
}
```

### GET `/api/articles/{topic_id}`
Same structure but filtered to one topic.

### GET `/api/insights`
```json
{
  "generated_at": "2026-05-24T06:00:00Z",
  "market_sectors_up": [
    {"sector": "Defence", "reason": "...", "source_event": "..."}
  ],
  "market_sectors_down": [
    {"sector": "Semiconductors", "reason": "...", "source_event": "..."}
  ]
}
```

### POST `/api/refresh`
Triggers an immediate pipeline run outside the scheduled interval. Returns:
```json
{"status": "started", "run_id": 42}
```

---

## 10. Scheduler & Automation

### 10.1 APScheduler (In-Process)

Used while the FastAPI server is running. Defined in `scheduler.py`:

```
Job 1: fetch_and_process()    — every 60 minutes
Job 2: run_derived_insights() — daily at 06:00 AM
Job 3: send_digest()          — daily at 08:00 AM and 08:00 PM
Job 4: cleanup_old_articles() — daily at 02:00 AM (delete > 30 days)
```

### 10.2 macOS launchd (Background Service)

A `.plist` file in `launchd/` starts the FastAPI server automatically at login and restarts it on crash. This ensures the dashboard is always available without manually running a terminal command.

The server starts on `localhost:8000`. Open any browser and navigate to `http://localhost:8000`.

---

## 11. Topic Classification System

### 11.1 Priority Resolution Example

An article from VentureBeat titled "Anthropic raises $2B Series E":

- Check `geopolitics_india` keywords → no match
- Check `geopolitics` keywords → no match
- Check `it_funding` keywords → **match** (raises, Series E)
- **Assigned: it_funding** — classifier stops here

An article from The Hindu titled "India-China border tensions impact semiconductor supply":

- Check `geopolitics_india` keywords → **match** (India, China border)
- **Assigned: geopolitics_india** — classifier stops here

### 11.2 Keyword Matching

- Case-insensitive
- Partial word match (e.g. "automation" matches "automated")
- Checked against: `title + description` concatenated
- Keywords in `sources.yaml` under each topic — editable without code changes

---

## 12. LLM Integration

### 12.1 API Keys

Stored in `.env` only. Never hardcoded. Never committed to git.

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...        # fallback only
LLM_PROVIDER=anthropic       # 'anthropic' or 'openai'
SUMMARISE_MODEL=claude-haiku-4
ANALYSIS_MODEL=claude-sonnet-4
```

### 12.2 Cost Estimate

At ~300 articles/day, avg 500 tokens per article:
- Input: 300 × 500 = 150,000 tokens/day
- Claude Haiku pricing: ~$0.25 per 1M input tokens
- **Estimated daily cost: ~₹3–5/day**

Derived insights (topics 3, 4, 8): 1 call/day, ~4,000 tokens. Negligible.

### 12.3 Fallback Behaviour

If LLM API is unavailable or returns an error:
- Article is written to DB without a summary
- Dashboard shows article with title + raw description snippet (first 200 chars)
- Summarisation is retried on the next pipeline run
- System never blocks or crashes due to LLM unavailability

---

## 13. Build Phases

| Phase | Scope | Deliverable |
|-------|-------|-------------|
| **1** | RSS fetcher, deduplicator, keyword classifier, SQLite, FastAPI dashboard (no summaries) | Working localhost dashboard, all 12 topics, no LLM |
| **2** | LLM summarisation via Claude Haiku, caching | All articles have 2-sentence summaries |
| **3** | Derived topics (3, 4, 8) via Claude Sonnet | Market sector insights + unconventional AI section |
| **4** | Email digest + launchd service | Auto-running background service, daily emails |
| **5** | Embedding dedup, authority scoring, mark-as-read | Quality layer, reduced noise, read tracking |

---

## 14. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Pipeline run time | < 3 minutes for full fetch + classify cycle |
| Dashboard page load | < 500ms (all data from local SQLite) |
| Feed fetch failure tolerance | Any single feed failure must not block the pipeline |
| LLM failure tolerance | System must function without summaries if API is down |
| Data retention | Articles kept for 30 days, then purged |
| Uptime | Best-effort; restarts automatically via launchd on crash |

---

## 15. Security Considerations

- **API keys** — stored in `.env` only, listed in `.gitignore`
- **No authentication** — single-user local tool, no login required
- **No external data exposure** — all data stays on localhost
- **No user input in SQL** — all DB writes use parameterised queries via SQLAlchemy
- **Feed content** — treat all fetched content as untrusted; strip HTML before storing
