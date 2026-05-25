import logging
from datetime import datetime, timezone

from sqlalchemy import select

from newsdash.config import load_config, get_enabled_feeds, get_topics, get_pipeline_config, get_github_config
from newsdash.db.models import RawItem, Article, PipelineRun, create_db_engine, init_db, get_session_factory
from newsdash.fetchers.rss import run_rss_fetch
from newsdash.fetchers.github import run_github_fetch
from newsdash.pipeline.dedupe import run_dedupe
from newsdash.pipeline.classify import classify_batch
from newsdash.pipeline.summarise import generate_insights

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
                
                # Use source's explicitly defined topic if available, fallback to keyword classification
                feed_topics = source.get("topics", [])
                final_topic_id = feed_topics[0] if feed_topics else item_dict["topic_id"]

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
                    topic_id=final_topic_id,
                )
                session.add(article)
                stored += 1

            run_record.items_classified = stored

            # Mark raw items as processed
            for item in raw_items:
                item.processed = True

            # Commit fetched and classified articles first
            await session.commit()

            # Step 6: Generate AI Insights / Summaries
            try:
                from newsdash.pipeline.impact import score_geopolitics_impact
                await score_geopolitics_impact(session, model_name="gemma2:2b")
                
                await generate_insights(session, topics, model_name="gemma2:2b")
                run_record.items_summarised = len(topics)
            except Exception as se:
                logger.error(f"Local AI summarization failed, but continuing: {se}", exc_info=True)

            # Step 7: Run Derived Topics (Market Analysis & AI Novelty)
            try:
                from newsdash.pipeline.derived import run_market_sector_analysis, run_ai_novelty_classification
                await run_market_sector_analysis(session, model_name="gemma2:2b")
                await run_ai_novelty_classification(session, model_name="gemma2:2b")
            except Exception as de:
                logger.error(f"Derived topics analysis failed, but continuing: {de}", exc_info=True)

            run_record.finished_at = datetime.now(timezone.utc)
            run_record.status = "success"
            await session.commit()

            logger.info(
                f"Pipeline complete: {fetched} fetched, {len(unique_items)} unique, "
                f"{stored} classified, {github_stored} GitHub repos, AI summaries generated."
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
