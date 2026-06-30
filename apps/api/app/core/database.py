from collections.abc import AsyncIterator

from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


def create_engine() -> AsyncEngine:
    settings = get_settings()
    options = {"pool_pre_ping": True}
    if not settings.database_pool_enabled:
        options["poolclass"] = NullPool
    return create_async_engine(settings.database_url, **options)


engine = create_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
