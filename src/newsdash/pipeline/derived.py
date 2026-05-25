import json
import logging
from datetime import datetime, timezone, timedelta, date
import ollama
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from newsdash.db.models import Article, DerivedInsight

logger = logging.getLogger(__name__)

MARKET_SECTORS_PROMPT = """You are a financial and geopolitical analyst. Based on the following geopolitical news headlines from the last 24 hours, identify:
A) Up to 2 market sectors likely to benefit (tailwinds)
B) Up to 2 market sectors likely to face headwinds

Format your answer as a JSON object with this exact structure:
{{
  "up": [{{"sector": "Sector Name", "reason": "One-sentence reasoning", "event": "Specific headline driving this inference"}}],
  "down": [{{"sector": "Sector Name", "reason": "One-sentence reasoning", "event": "Specific headline driving this inference"}}]
}}

Ensure the output is valid JSON and only the JSON object. Do not include any reasoning or conversational text. Start directly with the JSON block.

News headlines:
{news}
"""

AI_NOVELTY_PROMPT = """You are evaluating whether an AI news article describes a highly novel, non-obvious breakthrough or unconventional application of AI in a hard domain (e.g. drug discovery, climate modeling, robotics, scientific discovery, astrophysics, protein folding).

Article Title: {title}
Description: {description}

Evaluate the article and assign a novelty score from 1 to 10:
- Score 8-10: Truly breakthrough research, highly unconventional scientific domain, or profound architectural advancement (e.g., AlphaFold 3, custom robots, major AI-driven physics/chemistry breakthroughs).
- Score 4-7: Average business AI applications, standard software improvements, enterprise adoptions, or minor LLM updates.
- Score 1-3: Generic tech news, hiring updates, general opinion articles, or standard marketing launches.

Format your response exactly as a JSON object:
{{
  "score": N,
  "reason": "One-sentence explanation"
}}
Do not output any introductory or conversational text, only the JSON block. Start directly with the JSON block.
"""


def _clean_json_response(raw_text: str) -> str:
    """Helper to strip markdown code fences or conversational filler from LLM response."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


async def run_market_sector_analysis(session: AsyncSession, model_name: str = "gemma2:2b"):
    """Generate structured market sector tailwinds/headwinds from today's geopolitics articles."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await session.execute(
        select(Article)
        .where(and_(
            Article.topic_id.in_(["geopolitics", "geopolitics_india"]),
            Article.fetched_at >= cutoff
        ))
        .order_by(Article.source_tier, Article.published_at.desc())
        .limit(20)
    )
    articles = result.scalars().all()

    if not articles:
        logger.info("No geopolitics articles found in the last 24 hours for market analysis.")
        return

    news_lines = []
    for a in articles:
        desc = a.summary or a.title
        news_lines.append(f"- {a.title} ({a.source_name}): {desc[:150]}...")
    
    news_text = "\n".join(news_lines)
    prompt = MARKET_SECTORS_PROMPT.format(news=news_text)

    try:
        client = ollama.AsyncClient()
        response = await client.generate(model=model_name, prompt=prompt)
        raw_output = response.get("response", "").strip()
        cleaned_output = _clean_json_response(raw_output)
        
        data = json.loads(cleaned_output)
        today = datetime.now(timezone.utc).date()

        # Update market_sectors_up
        up_sectors = data.get("up", [])
        if up_sectors:
            content_up = "\n".join([
                f"**{s.get('sector', 'N/A')}** — {s.get('reason', '')} *(Re: {s.get('event', '')})*"
                for s in up_sectors
            ])
            # Check for existing up-insight today
            existing_up = await session.execute(
                select(DerivedInsight).where(
                    DerivedInsight.topic_id == "market_sectors_up",
                    DerivedInsight.date == today
                )
            )
            insight_up = existing_up.scalar_one_or_none()
            if insight_up:
                insight_up.content = content_up
                insight_up.generated_at = datetime.now(timezone.utc)
            else:
                insight_up = DerivedInsight(
                    topic_id="market_sectors_up",
                    content=content_up,
                    date=today,
                    source_article_ids=",".join(str(a.id) for a in articles)
                )
                session.add(insight_up)

        # Update market_sectors_down
        down_sectors = data.get("down", [])
        if down_sectors:
            content_down = "\n".join([
                f"**{s.get('sector', 'N/A')}** — {s.get('reason', '')} *(Re: {s.get('event', '')})*"
                for s in down_sectors
            ])
            existing_down = await session.execute(
                select(DerivedInsight).where(
                    DerivedInsight.topic_id == "market_sectors_down",
                    DerivedInsight.date == today
                )
            )
            insight_down = existing_down.scalar_one_or_none()
            if insight_down:
                insight_down.content = content_down
                insight_down.generated_at = datetime.now(timezone.utc)
            else:
                insight_down = DerivedInsight(
                    topic_id="market_sectors_down",
                    content=content_down,
                    date=today,
                    source_article_ids=",".join(str(a.id) for a in articles)
                )
                session.add(insight_down)

        await session.commit()
        logger.info("Local market sector analysis successfully completed and stored.")

    except Exception as e:
        logger.error(f"Market sector analysis via local LLM failed: {e}", exc_info=True)


async def run_ai_novelty_classification(session: AsyncSession, model_name: str = "gemma2:2b"):
    """Evaluate recent AI Space News articles and reclassify cutting-edge breakthroughs to Unconventional AI."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    result = await session.execute(
        select(Article)
        .where(and_(
            Article.topic_id == "ai_news",
            Article.fetched_at >= cutoff
        ))
        .order_by(Article.published_at.desc())
        .limit(20) # Limit to top 20 to run quickly
    )
    articles = result.scalars().all()

    if not articles:
        logger.info("No AI Space News articles found in the last 48 hours for novelty evaluation.")
        return

    logger.info(f"Evaluating {len(articles)} AI articles for unconventional breakthroughs.")
    client = ollama.AsyncClient()
    reclassified = 0

    for article in articles:
        prompt = AI_NOVELTY_PROMPT.format(
            title=article.title,
            description=article.summary or article.title
        )
        try:
            response = await client.generate(model=model_name, prompt=prompt)
            raw_output = response.get("response", "").strip()
            cleaned_output = _clean_json_response(raw_output)
            data = json.loads(cleaned_output)
            
            score = int(data.get("score", 0))
            reason = data.get("reason", "")
            
            if score >= 8:
                article.topic_id = "ai_nonconventional"
                # Store the reason as the article summary to highlight the LLM's classification!
                article.summary = f"[AI Breakthrough Score {score}/10]: {reason} (Original title: {article.title})"
                reclassified += 1
                logger.info(f"Reclassified article to Unconventional AI (Score {score}/10): {article.title}")
        except Exception as e:
            # Silently continue on JSON formatting or LLM errors
            logger.debug(f"Failed to evaluate article {article.id} for novelty: {e}")
            continue

    if reclassified > 0:
        await session.commit()
    logger.info(f"AI novelty classification finished. {reclassified} articles reclassified as unconventional.")
