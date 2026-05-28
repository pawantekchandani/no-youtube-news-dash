import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from newsdash.db.models import Article, DerivedInsight
from newsdash.config import load_config

logger = logging.getLogger(__name__)

TOPIC_ORDER = [
    "geopolitics_india",
    "geopolitics",
    "ai_news",
    "ai_business",
    "ai_jobs",
    "ai_nonconventional",
    "it_news",
    "it_launches",
    "github_trending",
    "it_funding",
    "market_sectors_up",
    "market_sectors_down",
]

async def generate_brief_markdown(session: AsyncSession) -> str:
    """Generate a clean, professional Markdown news brief optimized for Gemini mobile app reading."""
    logger.info("Generating markdown news brief...")
    
    # 24-hour cutoff
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    config = load_config()
    topics = config.get("topics", [])
    topic_labels = {t["id"]: t["label"] for t in topics}

    # Fetch recent articles
    result = await session.execute(
        select(Article)
        .where(Article.fetched_at >= cutoff)
    )
    articles = result.scalars().all()

    grouped_articles = {}
    for a in articles:
        grouped_articles.setdefault(a.topic_id, []).append(a)

    # Fetch today's insights in IST
    # IST is UTC+5:30. Let's calculate today's date in IST
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    today_ist = ist_now.date()
    
    insight_result = await session.execute(
        select(DerivedInsight)
        .where(DerivedInsight.date == today_ist)
    )
    insights = {i.topic_id: i for i in insight_result.scalars().all()}

    # Calculate total headlines
    total_headlines = 0
    for topic_id in TOPIC_ORDER:
        if topic_id in ("market_sectors_up", "market_sectors_down"):
            continue
        topic_articles = grouped_articles.get(topic_id, [])
        if topic_id == "geopolitics_india":
            total_headlines += len(topic_articles[:3])
        else:
            total_headlines += len(topic_articles[:10])

    # Header block
    timestamp_str = ist_now.strftime('%d %b %Y, %H:%M IST')
    lines = [
        f"# No-YouTube News Dash: Daily Brief",
        f"**Generated:** {timestamp_str} | **Total Fresh Headlines:** {total_headlines}",
        "",
        "---",
        ""
    ]

    # Render topics in order
    for topic_id in TOPIC_ORDER:
        label = topic_labels.get(topic_id, topic_id).upper()
        insight = insights.get(topic_id)
        topic_articles = grouped_articles.get(topic_id, [])

        # Synthesis/derived-only topics or standard topics
        is_market = topic_id in ("market_sectors_up", "market_sectors_down")

        if is_market:
            if not insight:
                continue
            lines.append(f"## {label}")
            lines.append(f"> **AI Trend Synthesis:**")
            # format blockquote lines properly
            for val_line in insight.content.strip().split("\n"):
                lines.append(f"> {val_line}")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        # For standard topics, skip if there are no fresh articles and no AI briefing
        if not topic_articles and not insight:
            continue

        lines.append(f"## {label}")
        
        # 1. Daily AI briefing card
        if insight:
            lines.append(f"> **AI Sector Briefing:**")
            for val_line in insight.content.strip().split("\n"):
                lines.append(f"> {val_line}")
            lines.append("")

        # 2. List recent articles
        if topic_articles:
            # Sort order:
            # geopolitics_india: impact_score desc, limit 3
            # others: source_tier asc, published_at desc, limit 10
            if topic_id == "geopolitics_india":
                sorted_articles = sorted(
                    topic_articles, 
                    key=lambda x: (x.impact_score or 0), 
                    reverse=True
                )[:3]
            else:
                # None checks for published_at/source_tier
                sorted_articles = sorted(
                    topic_articles, 
                    key=lambda x: (x.source_tier or 2, -(x.published_at.timestamp() if x.published_at else 0))
                )[:10]

            for i, a in enumerate(sorted_articles, 1):
                impact_suffix = f" (Impact: {a.impact_score}/10)" if (topic_id == "geopolitics_india" and a.impact_score) else ""
                if a.url:
                    lines.append(f"{i}. **[{a.title}]({a.url})** — *{a.source_name}*{impact_suffix}")
                else:
                    lines.append(f"{i}. **{a.title}** — *{a.source_name}*{impact_suffix}")
                if a.summary and not a.summary.startswith("[AI"):
                    lines.append(f"   Summary: {a.summary.strip()}")
                lines.append("")

        else:
            lines.append("*No new developments fetched in the last 24 hours.*")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append("## END OF BRIEFING")
    return "\n".join(lines)
