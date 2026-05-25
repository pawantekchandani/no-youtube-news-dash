import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
import ollama

from newsdash.db.models import Article

logger = logging.getLogger(__name__)


async def score_geopolitics_impact(session, model_name="gemma2:2b"):
    """
    Score articles in geopolitics_india topic for their actual impact.
    Updates the impact_score column in the database.
    """
    since_time = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await session.execute(
        select(Article).where(
            Article.fetched_at >= since_time,
            Article.topic_id == "geopolitics_india",
            Article.impact_score == 0
        )
    )
    articles = result.scalars().all()
    
    if not articles:
        return

    logger.info(f"Scoring impact for {len(articles)} geopolitics_india articles.")
    client = ollama.AsyncClient()

    for article in articles:
        prompt = f"""You are a geopolitical analyst for India. 
Rate the following news development on a scale of 1 to 10 based on its actual strategic, economic, or security impact on India's geopolitics.
10 = Massive paradigm-shifting event (e.g. major war, huge treaty, severe sanctions)
1 = Minor or routine event (e.g. routine meeting, standard commentary)

Title: {article.title}
Summary: {article.summary or article.title}

Respond with ONLY the integer score (e.g. 8). No explanation. No other text."""
        try:
            response = await client.generate(model=model_name, prompt=prompt)
            score_text = response.get("response", "").strip()
            
            # Extract digits
            score_digits = "".join(c for c in score_text if c.isdigit())
            if score_digits:
                score = int(score_digits)
                article.impact_score = min(max(score, 1), 10)
            else:
                article.impact_score = 1
        except Exception as e:
            logger.error(f"Failed to score article {article.id}: {e}")
            article.impact_score = 1

    await session.commit()
    logger.info("Finished scoring impact.")
