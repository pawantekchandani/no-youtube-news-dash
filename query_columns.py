import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, desc
from src.newsdash.server.app import session_factory, Article
from src.newsdash.config import load_config

async def main():
    config = load_config()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    async with session_factory() as session:
        result = await session.execute(
            select(Article)
            .where(Article.published_at >= cutoff)
            .where(Article.topic_id.in_(['geopolitics_india', 'geopolitics']))
            .order_by(Article.source_tier.asc(), desc(Article.published_at))
        )
        articles = result.scalars().all()
    
    grouped = {}
    for a in articles:
        grouped.setdefault(a.topic_id, []).append(a)
    
    if "geopolitics_india" in grouped:
        grouped["geopolitics_india"].sort(key=lambda a: (a.impact_score or 0), reverse=True)
        grouped["geopolitics_india"] = grouped["geopolitics_india"][:3]
        
    for k, v in grouped.items():
        print(f"--- Section: {k} ---")
        for a in v:
            print(f"- {a.title} (Score: {a.impact_score})")

if __name__ == '__main__':
    asyncio.run(main())
