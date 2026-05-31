import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

error_file_handler = logging.FileHandler("logs/errors.log")
error_file_handler.setLevel(logging.ERROR)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/newsdash.log"),
        error_file_handler,
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
    
    # Set up database engine and session factory
    from apscheduler.triggers.cron import CronTrigger
    from newsdash.db.models import create_db_engine, get_session_factory

    engine = create_db_engine()
    session_factory = get_session_factory(engine)

    # Register Google Drive brief upload jobs
    from newsdash.digest.drive_uploader import run_drive_upload
    import json
    from datetime import datetime, timezone, timedelta

    STATE_FILE = "config/upload_state.json"

    async def trigger_drive_upload_if_needed():
        drive_brief_cfg = config.get("drive_brief", {})
        if not drive_brief_cfg.get("enabled", False):
            return

        schedule = drive_brief_cfg.get("schedule", ["07:00", "19:00"])
        ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        current_time_str = ist_now.strftime('%H:%M')
        date_str = ist_now.strftime('%Y-%m-%d')

        target_shift = None
        for time_str in sorted(schedule):
            if current_time_str >= time_str:
                target_shift = time_str

        if not target_shift:
            return

        shift_key = f"{date_str}_{target_shift}"
        
        state = {}
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        if state.get("last_uploaded_shift") == shift_key:
            return

        logging.info(f"Triggering Google Drive upload for shift {shift_key}")
        async with session_factory() as session:
            folder = drive_brief_cfg.get("folder_name", "Newsdash Daily Briefs")
            try:
                await run_drive_upload(session, folder_name=folder, target_shift=target_shift)
                state["last_uploaded_shift"] = shift_key
                with open(STATE_FILE, "w") as f:
                    json.dump(state, f)
                logging.info(f"Successfully recorded upload state for shift {shift_key}")
            except Exception as e:
                logging.error(f"Drive upload failed, will retry in 15 mins: {e}")

    drive_brief_cfg = config.get("drive_brief", {})
    if drive_brief_cfg.get("enabled", False):
        scheduler.add_job(
            trigger_drive_upload_if_needed,
            IntervalTrigger(minutes=15),
            id="drive_brief_check"
        )
        logging.info("Google Drive upload check scheduled every 15 minutes.")

    scheduler.start()

    # Run once immediately on startup
    asyncio.create_task(run_pipeline())
    if drive_brief_cfg.get("enabled", False):
        asyncio.create_task(trigger_drive_upload_if_needed())

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
