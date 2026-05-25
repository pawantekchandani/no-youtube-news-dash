import asyncio
from src.newsdash.server.app import session_factory, Article
from src.newsdash.config import load_config
from sqlalchemy import select

async def main():
    config = load_config()
    feeds = config.get("feeds", [])
    source_lookup = {f["id"]: f.get("topics", [None])[0] for f in feeds if f.get("topics")}

    async with session_factory() as session:
        result = await session.execute(select(Article))
        articles = result.scalars().all()
        
        updated = 0
        for a in articles:
            correct_topic = source_lookup.get(a.source_id)
            if correct_topic and a.topic_id != correct_topic:
                a.topic_id = correct_topic
                updated += 1
        
        await session.commit()
        print(f"Updated {updated} articles.")

if __name__ == '__main__':
    asyncio.run(main())
