import logging
import os
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from newsdash.db.models import Article, DerivedInsight
from newsdash.config import load_config

logger = logging.getLogger(__name__)

TOPIC_ORDER = [
    "geopolitics_india", "geopolitics",
    "ai_news", "ai_business", "ai_jobs", "ai_nonconventional",
    "it_news", "it_launches", "github_trending", "it_funding",
]


async def build_digest(session: AsyncSession, top_n: int = 5) -> str:
    """Compile the plain-text intelligence digest integrating articles, AI topic briefs, and VC market insights."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    config = load_config()
    topics = config.get("topics", [])
    topic_labels = {t["id"]: t["label"] for t in topics}

    # Fetch recent articles
    result = await session.execute(
        select(Article)
        .where(Article.fetched_at >= cutoff)
        .order_by(desc(Article.published_at))
    )
    articles = result.scalars().all()

    grouped_articles = {}
    for a in articles:
        grouped_articles.setdefault(a.topic_id, []).append(a)

    # Fetch today's insights
    today = datetime.now(timezone.utc).date()
    insight_result = await session.execute(
        select(DerivedInsight)
        .where(DerivedInsight.date == today)
    )
    insights = {i.topic_id: i for i in insight_result.scalars().all()}

    lines = [
        "============================================================",
        f"       INTELLIGENCE BRIEFING & GEOPOLITICAL TECH DIGEST     ",
        f"               {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')}               ",
        "============================================================",
        "",
        "This daily briefing is compiled locally by your Geopolitics & Tech",
        "Intelligence Dashboard. Summaries and market insights were synthesized",
        "entirely offline using Google Gemma 2B.",
        "",
    ]

    # Render standard columns/topics
    lines.append("============================================================")
    lines.append("                   COLUMN BRIEFS & DEVELOPMENTS             ")
    lines.append("============================================================")
    
    for topic_id in TOPIC_ORDER:
        topic_articles = grouped_articles.get(topic_id, [])
        insight = insights.get(topic_id)
        
        # Only show sections that have fresh articles or an LLM summary
        if not topic_articles and not insight:
            continue

        label = topic_labels.get(topic_id, topic_id).upper()
        lines.append(f"\n{label}")
        lines.append("-" * len(label))
        
        # 1. Embed daily AI briefing card if generated
        if insight:
            lines.append(f"\n[LOCAL AI BRIEFING]:")
            lines.append(f"{insight.content}")
            lines.append("")

        # 2. List recent articles
        if topic_articles:
            lines.append("Recent Developments:")
            for a in topic_articles[:top_n]:
                lines.append(f"• {a.title}")
                lines.append(f"  [{a.source_name}] - {a.url}")
                if a.summary and not a.summary.startswith("[AI"): # Don't repeat classification summaries
                    lines.append(f"  {a.summary}")
                lines.append("")
        else:
            lines.append("No new developments fetched in the last 24 hours.\n")

    # Render synthesized derived markets column
    lines.append("\n============================================================")
    lines.append("                   DERIVED MARKET SYSTHESIS & TRENDS        ")
    lines.append("============================================================")

    market_topics = [
        ("market_sectors_up", "SECTORS TO WATCH — VENTURE TAILWINDS"),
        ("market_sectors_down", "SECTORS UNDER PRESSURE — RISK HEADWINDS"),
        ("ai_nonconventional", "UNCONVENTIONAL AI USE CASES & LAB BREAKER DEALS")
    ]

    for topic_id, header in market_topics:
        insight = insights.get(topic_id)
        if insight:
            lines.append(f"\n{header}")
            lines.append("-" * len(header))
            lines.append(insight.content)
            lines.append("")

    lines.append("\n============================================================")
    lines.append("End of Intelligence Briefing.")
    lines.append("============================================================")

    return "\n".join(lines)


async def send_digest(session: AsyncSession):
    """Compile and send email digest to configured recipient via SMTP."""
    config = load_config()
    digest_cfg = config.get("digest", {})

    if not digest_cfg.get("enabled", False):
        logger.info("Email digest is disabled in sources.yaml. Skipping daily email.")
        return

    recipient = digest_cfg.get("recipient_email") or os.getenv("DIGEST_RECIPIENT_EMAIL")
    sender = digest_cfg.get("sender_email", "newsdash@localhost")
    smtp_host = os.getenv("DIGEST_SMTP_HOST") or digest_cfg.get("smtp_host", "localhost")
    smtp_port = int(os.getenv("DIGEST_SMTP_PORT") or digest_cfg.get("smtp_port", 25))
    top_n = digest_cfg.get("top_n_per_topic", 5)

    smtp_user = os.getenv("DIGEST_SMTP_USER") or digest_cfg.get("smtp_user")
    smtp_password = os.getenv("DIGEST_SMTP_PASSWORD") or digest_cfg.get("smtp_password")
    
    smtp_use_tls_raw = os.getenv("DIGEST_SMTP_USE_TLS") or digest_cfg.get("smtp_use_tls")
    if isinstance(smtp_use_tls_raw, str):
        smtp_use_tls = smtp_use_tls_raw.lower() in ("true", "1", "yes")
    elif smtp_use_tls_raw is not None:
        smtp_use_tls = bool(smtp_use_tls_raw)
    else:
        smtp_use_tls = (smtp_port == 587)

    smtp_use_ssl_raw = os.getenv("DIGEST_SMTP_USE_SSL") or digest_cfg.get("smtp_use_ssl")
    if isinstance(smtp_use_ssl_raw, str):
        smtp_use_ssl = smtp_use_ssl_raw.lower() in ("true", "1", "yes")
    elif smtp_use_ssl_raw is not None:
        smtp_use_ssl = bool(smtp_use_ssl_raw)
    else:
        smtp_use_ssl = (smtp_port == 465)

    if not recipient:
        logger.warning("No recipient email configured for digest. Set DIGEST_RECIPIENT_EMAIL.")
        return

    logger.info(f"Compiling local intelligence digest email for {recipient}...")
    body = await build_digest(session, top_n)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Intelligence Briefing — {datetime.now(timezone.utc).strftime('%d %b %Y')} UTC"
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(body, "plain"))

    try:
        if smtp_use_ssl:
            logger.info(f"Connecting to SMTP server {smtp_host}:{smtp_port} using SSL...")
            smtp_client = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            logger.info(f"Connecting to SMTP server {smtp_host}:{smtp_port}...")
            smtp_client = smtplib.SMTP(smtp_host, smtp_port)
            
        with smtp_client as smtp:
            if not smtp_use_ssl and smtp_use_tls:
                logger.info("Securing SMTP connection with STARTTLS...")
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
            if smtp_user and smtp_password:
                logger.info(f"Logging in to SMTP server as {smtp_user}...")
                smtp.login(smtp_user, smtp_password)
            logger.info(f"Sending email from {sender} to {recipient}...")
            smtp.sendmail(sender, [recipient], msg.as_string())
        logger.info(f"Daily intelligence brief email sent successfully to {recipient}")
    except Exception as e:
        logger.error(f"Failed to send email digest: {e}", exc_info=True)
        raise e

