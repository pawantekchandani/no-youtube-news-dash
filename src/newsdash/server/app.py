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
            .order_by(Article.source_tier.asc(), desc(Article.published_at))
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

    # Sort and filter geopolitics_india by highest impact
    if "geopolitics_india" in grouped:
        grouped["geopolitics_india"].sort(key=lambda a: (a.impact_score or 0), reverse=True)
        grouped["geopolitics_india"] = grouped["geopolitics_india"][:3]

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

    total_articles = sum(len(items) for items in grouped.values())

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "grouped": grouped,
            "columns": columns,
            "topic_labels": topic_labels,
            "insights": insights,
            "generated_at": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
            "refresh_seconds": 1800,
            "total_articles": total_articles,
        }
    )


@app.get("/api/articles")
async def get_articles():
    config = load_config()
    age_hours = get_pipeline_config(config).get("dashboard_article_age_hours", 24)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=age_hours)

    async with session_factory() as session:
        result = await session.execute(
            select(Article)
            .where(Article.published_at >= cutoff)
            .order_by(Article.source_tier.asc(), desc(Article.published_at))
        )
        articles = result.scalars().all()

    grouped = {}
    for a in articles:
        grouped.setdefault(a.topic_id, []).append({
            "id": a.id, "title": a.title, "url": a.url,
            "summary": a.summary, "source_name": a.source_name,
            "source_tier": a.source_tier,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "read": a.read,
            "impact_score": a.impact_score
        })

    if "geopolitics_india" in grouped:
        grouped["geopolitics_india"].sort(key=lambda a: (a.get("impact_score") or 0), reverse=True)
        grouped["geopolitics_india"] = grouped["geopolitics_india"][:3]

    return {"generated_at": datetime.now(timezone.utc).isoformat(), "topics": grouped}


@app.post("/api/articles/{article_id}/read")
async def mark_read(article_id: int):
    async with session_factory() as session:
        result = await session.execute(select(Article).where(Article.id == article_id))
        article = result.scalar_one_or_none()
        if article:
            article.read = True
            await session.commit()
    return {"status": "ok"}


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
