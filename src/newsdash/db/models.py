from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Text,
    Index, create_engine
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from datetime import datetime, timezone
import os


class Base(DeclarativeBase):
    pass


class RawItem(Base):
    __tablename__ = "raw_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False)
    url_hash = Column(String(64), nullable=False, unique=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_id = Column(String(100), nullable=False)
    processed = Column(Boolean, default=False)


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False)
    url_hash = Column(String(64), nullable=False, unique=True)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    summary_cached = Column(Boolean, default=False)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_id = Column(String(100), nullable=False)
    source_name = Column(String(200), nullable=False)
    source_tier = Column(Integer, default=2)
    topic_id = Column(String(100), nullable=False)
    read = Column(Boolean, default=False)
    impact_score = Column(Integer, default=0)


class DerivedInsight(Base):
    __tablename__ = "derived_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(String(100), nullable=False)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    content = Column(Text, nullable=False)
    source_article_ids = Column(Text)
    date = Column(Date, nullable=False)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime)
    items_fetched = Column(Integer, default=0)
    items_deduped = Column(Integer, default=0)
    items_classified = Column(Integer, default=0)
    items_summarised = Column(Integer, default=0)
    status = Column(String(20))
    error_message = Column(Text)


# Indexes
Index("idx_articles_topic", Article.topic_id)
Index("idx_articles_published", Article.published_at)
Index("idx_articles_url_hash", Article.url_hash)
Index("idx_raw_items_processed", RawItem.processed)


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/news.db")


def create_db_engine():
    url = get_database_url()
    return create_async_engine(url, echo=False)


async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
