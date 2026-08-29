"""Database connection management for Postgres and Redis."""

from typing import AsyncGenerator, Optional
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from mcp_digitalinvoice.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency / helper for async database session context."""
    async with AsyncSessionLocal() as session:
        yield session


def get_redis_client() -> Optional[Redis]:
    """Return a configured Redis async client instance or None if unavailable."""
    try:
        return Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception as exc:
        return None
