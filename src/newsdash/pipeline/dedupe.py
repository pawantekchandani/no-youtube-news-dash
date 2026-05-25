import logging
import os
from datetime import datetime, timezone, timedelta

from rapidfuzz import fuzz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from newsdash.db.models import RawItem, Article

logger = logging.getLogger(__name__)

_model = None

def get_embedding_model():
    global _model
    if _model is None:
        try:
            logger.info("Loading sentence-transformers model (all-MiniLM-L6-v2) for semantic deduplication...")
            from sentence_transformers import SentenceTransformer
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence-transformers model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load sentence-transformers model: {e}. Falling back to fuzzy matching.")
    return _model


async def get_recent_titles(session: AsyncSession, window_hours: int) -> list[tuple[str, str, int]]:
    """Return (url_hash, title, source_tier) for articles in the dedup window."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    result = await session.execute(
        select(Article.url_hash, Article.title, Article.source_tier)
        .where(Article.fetched_at >= cutoff)
    )
    return result.fetchall()


async def run_dedupe(
    session: AsyncSession,
    raw_items: list[RawItem],
    window_hours: int,
    threshold: int,
) -> list[RawItem]:
    """
    Given a list of unprocessed RawItems, return only those that pass dedup.
    Stage 1: URL hash not in articles table.
    Stage 2: Title not semantically or fuzzily similar to any recent article.
    """
    recent = await get_recent_titles(session, window_hours)
    recent_hashes = {row[0] for row in recent}
    recent_titles = [(row[0], row[1], row[2]) for row in recent]

    passed = []
    skipped_exact = 0
    skipped_similar = 0

    # Stage 1: Filter exact URL hash matches first
    stage1_passed = []
    for item in raw_items:
        if item.url_hash in recent_hashes:
            skipped_exact += 1
        else:
            stage1_passed.append(item)

    if not stage1_passed:
        logger.info(
            f"Dedup: {len(raw_items)} in, 0 passed, "
            f"{skipped_exact} exact dupes, 0 near-dupes"
        )
        return []

    # Try embedding-based deduplication first if model is available and we have recent articles
    model = get_embedding_model()
    if model is not None and recent_titles:
        try:
            from sentence_transformers import util
            
            # Encode all recent titles at once
            existing_titles = [t[1] for t in recent_titles]
            existing_embeddings = model.encode(existing_titles, convert_to_tensor=True)
            
            # Encode the new batch titles
            new_titles = [item.title for item in stage1_passed]
            new_embeddings = model.encode(new_titles, convert_to_tensor=True)
            
            # Compute cosine similarity matrix
            similarity_matrix = util.cos_sim(new_embeddings, existing_embeddings)
            
            # Convert threshold from 0-100 scale to 0-1 scale
            sim_threshold = threshold / 100.0
            
            for idx, item in enumerate(stage1_passed):
                duplicate_found = False
                
                # Check similarity with existing articles
                for existing_idx, (existing_hash, existing_title, existing_tier) in enumerate(recent_titles):
                    score = similarity_matrix[idx][existing_idx].item()
                    if score >= sim_threshold:
                        duplicate_found = True
                        skipped_similar += 1
                        break
                
                if not duplicate_found:
                    passed.append(item)
                    # Add to recent_titles and re-encode to allow intra-batch deduplication
                    recent_titles.append((item.url_hash, item.title, 2))
                    
                    # Append the embedding to existing_embeddings for future checks in this batch
                    new_emb = new_embeddings[idx].unsqueeze(0)
                    import torch
                    existing_embeddings = torch.cat([existing_embeddings, new_emb], dim=0)
            
            logger.info(
                f"Semantic Dedup: {len(raw_items)} in, {len(passed)} passed, "
                f"{skipped_exact} exact dupes, {skipped_similar} near-dupes (semantic)"
            )
            return passed
        except Exception as ex:
            logger.error(f"Error during semantic deduplication: {ex}. Falling back to fuzzy matching.", exc_info=True)
            passed = []
            skipped_similar = 0

    # Fallback: fuzzy matching (rapidfuzz)
    for item in stage1_passed:
        duplicate_found = False
        for existing_hash, existing_title, existing_tier in recent_titles:
            score = fuzz.token_sort_ratio(
                item.title.lower(), existing_title.lower()
            )
            if score >= threshold:
                duplicate_found = True
                skipped_similar += 1
                break

        if not duplicate_found:
            passed.append(item)
            recent_titles.append((item.url_hash, item.title, 2))

    logger.info(
        f"Fuzzy Dedup: {len(raw_items)} in, {len(passed)} passed, "
        f"{skipped_exact} exact dupes, {skipped_similar} near-dupes (fuzzy)"
    )
    return passed

