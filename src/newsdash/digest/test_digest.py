import asyncio
import logging
from newsdash.db.models import create_db_engine, get_session_factory
from newsdash.digest.mailer import build_digest

async def test():
    engine = create_db_engine()
    session_factory = get_session_factory(engine)
    async with session_factory() as session:
        # Fetch the top 3 articles per topic for testing
        body = await build_digest(session, top_n=3)
        print("\n=== COMPILED EMAIL DIGEST OUTPUT ===\n")
        print(body)
        print("\n=====================================\n")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(test())
