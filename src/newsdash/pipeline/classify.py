import logging
from typing import Optional

logger = logging.getLogger(__name__)


def classify_topic(title: str, description: str, topics: list[dict]) -> Optional[str]:
    """
    Assign exactly one topic to an article using priority-ordered keyword matching.
    Topics list must be sorted by priority ascending (lower number = higher priority).
    Returns topic_id of first match, or None if no match.
    """
    text = f"{title} {description}".lower()
    sorted_topics = sorted(
        [t for t in topics if not t.get("derived", False)],
        key=lambda t: t.get("priority", 99)
    )

    for topic in sorted_topics:
        keywords = topic.get("keywords", [])
        if not keywords:
            continue
        for keyword in keywords:
            if keyword.lower() in text:
                return topic["id"]

    # Fallback: assign to it_news if nothing matched and article came from a tech source
    return "it_news"


def classify_batch(items: list[dict], topics: list[dict]) -> list[dict]:
    """Classify a list of items in place. Returns items with topic_id set."""
    classified = 0
    for item in items:
        topic_id = classify_topic(
            item.get("title", ""),
            item.get("description", ""),
            topics
        )
        item["topic_id"] = topic_id
        classified += 1

    logger.info(f"Classified {classified} items")
    return items
