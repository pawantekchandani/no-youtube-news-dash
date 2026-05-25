import logging
from datetime import datetime, timezone, timedelta
import json
import ollama
from sqlalchemy import select, delete
from newsdash.db.models import Article, DerivedInsight
from newsdash.config import get_topics

logger = logging.getLogger(__name__)


async def generate_insights(session, topics: list[dict], model_name: str = "gemma2:2b"):
    """
    Generate daily AI briefs for standard topics and derived insights for synthesized topics.
    Connects to the local Ollama daemon.
    """
    # 1. Fetch articles from the last 24 hours
    since_time = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await session.execute(
        select(Article).where(Article.fetched_at >= since_time)
    )
    all_recent_articles = result.scalars().all()
    
    if not all_recent_articles:
        logger.info("No articles fetched in the last 24 hours. Skipping AI summarization.")
        return

    logger.info(f"Generating AI Summaries using local model '{model_name}' for {len(all_recent_articles)} articles.")
    
    # Instantiate Ollama AsyncClient
    client = ollama.AsyncClient()

    # Group articles by topic
    articles_by_topic = {}
    for article in all_recent_articles:
        articles_by_topic.setdefault(article.topic_id, []).append(article)

    today = datetime.now(timezone.utc).date()

    # Define prompts and processes for standard topics
    for topic in topics:
        topic_id = topic["id"]
        topic_label = topic.get("label", topic_id)
        is_derived = topic.get("derived", False)

        if is_derived:
            continue

        topic_articles = articles_by_topic.get(topic_id, [])
        if not topic_articles:
            continue

        # Format developments for the LLM
        developments = []
        for a in topic_articles[:15]: # Limit to top 15 to prevent context blowing up on tiny models
            desc = (a.summary or a.title)
            developments.append(f"- {a.title} ({a.source_name})\n  Context: {desc[:200]}")
        
        devs_str = "\n".join(developments)

        prompt = f"""You are a professional intelligence analyst preparing a high-level briefing.
Below is a list of recent news developments for the category: "{topic_label}".

Developments:
{devs_str}

Write a concise, professional 1-2 sentence executive briefing summarizing these developments.
Rules:
1. Keep it strictly under 50 words.
2. Do NOT say "Here is a summary", "Sure, here is the briefing", or use introductory conversational filler. Start directly with the summary content.
3. Focus on the global impact, trend, or key takeaway.
4. If articles are not cohesive, summarize the single most important trend.
"""
        try:
            response = await client.generate(model=model_name, prompt=prompt)
            summary_content = response.get("response", "").strip()
            
            # Clean up potential leading/trailing quotes or filler
            if summary_content.startswith('"') and summary_content.endswith('"'):
                summary_content = summary_content[1:-1].strip()

            if summary_content:
                # Save or update DerivedInsight for today
                # First check if one exists
                existing = await session.execute(
                    select(DerivedInsight).where(
                        DerivedInsight.topic_id == topic_id,
                        DerivedInsight.date == today
                    )
                )
                insight = existing.scalar_one_or_none()
                
                article_ids_str = ",".join(str(a.id) for a in topic_articles)

                if insight:
                    insight.content = summary_content
                    insight.source_article_ids = article_ids_str
                    insight.generated_at = datetime.now(timezone.utc)
                else:
                    insight = DerivedInsight(
                        topic_id=topic_id,
                        content=summary_content,
                        source_article_ids=article_ids_str,
                        date=today
                    )
                    session.add(insight)
                
                logger.info(f"Generated daily summary for topic: {topic_id}")
        except Exception as e:
            logger.error(f"Failed to generate summary for topic {topic_id}: {e}", exc_info=True)

    # 2. Synthesize derived insights across ALL recent articles
    all_titles_desc = []
    for a in all_recent_articles[:30]: # Limit context to top 30
        all_titles_desc.append(f"- {a.title} | {a.source_name}: {a.summary or ''}")
    headlines_str = "\n".join(all_titles_desc)

    derived_configs = {
        "market_sectors_up": {
            "prompt": f"""You are a venture capital and market sector analyst. Based on the following tech and AI developments from the last 24 hours, identify 1-2 specific industries, sectors, or technical fields showing strong positive momentum, high investor interest, major funding, or growth tailwinds.

Developments:
{headlines_str}

Write a concise 2-sentence market briefing summarizing these positive sector tailwinds.
Rules:
1. Start directly with the briefing. Do NOT say "Here is a briefing" or use conversational filler.
2. Be highly professional and specific.
""",
        },
        "market_sectors_down": {
            "prompt": f"""You are a market risk analyst. Based on the following tech and AI developments from the last 24 hours, identify 1-2 sectors, companies, or technologies facing headwinds, budget cuts, job losses, automation displacements, or regulatory pressures.

Developments:
{headlines_str}

Write a concise 2-sentence briefing summarizing these negative sector headwinds and pressures.
Rules:
1. Start directly with the briefing. Do NOT say "Here is a briefing" or use conversational filler.
2. Be highly professional, realistic, and objective.
""",
        },
        "ai_nonconventional": {
            "prompt": f"""You are an advanced AI researcher. Scan the following tech and AI developments from the last 24 hours and identify any creative, highly unusual, scientific, or non-conventional applications of artificial intelligence (e.g. solving biology/physics, creative/artistic breakthroughs, niche and clever workflows).

Developments:
{headlines_str}

Write a concise 2-sentence briefing highlighting 1-2 of these unconventional AI use cases.
Rules:
1. Start directly with the briefing. Do NOT say "Here is a briefing" or use conversational filler.
2. If no unusual implementations are explicitly mentioned, summarize the most interesting technical approach.
""",
        }
    }

    for topic_id, config in derived_configs.items():
        # Only generate if there is matching derived topic configured
        if not any(t["id"] == topic_id for t in topics):
            continue
            
        try:
            response = await client.generate(model=model_name, prompt=config["prompt"])
            summary_content = response.get("response", "").strip()
            
            if summary_content.startswith('"') and summary_content.endswith('"'):
                summary_content = summary_content[1:-1].strip()

            if summary_content:
                existing = await session.execute(
                    select(DerivedInsight).where(
                        DerivedInsight.topic_id == topic_id,
                        DerivedInsight.date == today
                    )
                )
                insight = existing.scalar_one_or_none()
                
                article_ids_str = ",".join(str(a.id) for a in all_recent_articles)

                if insight:
                    insight.content = summary_content
                    insight.source_article_ids = article_ids_str
                    insight.generated_at = datetime.now(timezone.utc)
                else:
                    insight = DerivedInsight(
                        topic_id=topic_id,
                        content=summary_content,
                        source_article_ids=article_ids_str,
                        date=today
                    )
                    session.add(insight)
                
                logger.info(f"Generated derived insight for: {topic_id}")
        except Exception as e:
            logger.error(f"Failed to generate derived insight for {topic_id}: {e}", exc_info=True)

    await session.commit()
