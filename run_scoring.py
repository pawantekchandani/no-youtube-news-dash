import asyncio
from newsdash.db.models import create_db_engine, init_db, get_session_factory
from newsdash.pipeline.impact import score_geopolitics_impact

async def run():
    engine = create_db_engine()
    await init_db(engine)
    session_factory = get_session_factory(engine)
    async with session_factory() as session:
        await score_geopolitics_impact(session)
    print('Done scoring!')

asyncio.run(run())
