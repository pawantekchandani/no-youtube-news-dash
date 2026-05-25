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

from newsdash.config import load_config, get_pipeline_config
from newsdash.pipeline_runner import run_pipeline


async def main():
    config = load_config()
    pipeline_cfg = get_pipeline_config(config)
    interval_minutes = pipeline_cfg.get("fetch_interval_minutes", 60)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_pipeline, IntervalTrigger(minutes=interval_minutes), id="pipeline")
    
    # Register daily email digest jobs based on sources.yaml configuration
    from apscheduler.triggers.cron import CronTrigger
    from newsdash.db.models import create_db_engine, get_session_factory
    from newsdash.digest.mailer import send_digest

    engine = create_db_engine()
    session_factory = get_session_factory(engine)

    async def trigger_email_digest():
        async with session_factory() as session:
            await send_digest(session)

    digest_cfg = config.get("digest", {})
    if digest_cfg.get("enabled", False):
        digest_schedule = digest_cfg.get("schedule", ["08:00", "20:00"])
        for i, time_str in enumerate(digest_schedule):
            try:
                hour, minute = map(int, time_str.strip().split(":"))
                scheduler.add_job(
                    trigger_email_digest,
                    CronTrigger(hour=hour, minute=minute),
                    id=f"digest_{i}"
                )
                logging.info(f"Daily email digest scheduled at {time_str} (Job: digest_{i})")
            except Exception as se:
                logging.error(f"Failed to parse and schedule digest time '{time_str}': {se}")

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
