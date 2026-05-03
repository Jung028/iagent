from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from iagent.config import settings
from .models import WriteBase


def create_engine_and_factory() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    url = settings.database_url
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Add DATABASE_URL=postgresql://user@host:port/dbname to your .env file."
        )

    # asyncpg requires the postgresql+asyncpg:// scheme
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(
        url,
        pool_size=10,
        max_overflow=20,
        echo=False,
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return engine, session_factory


async def create_tables(engine: AsyncEngine) -> None:
    # Safe to call on every startup — checkfirst=True and IF NOT EXISTS skip existing objects.
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(WriteBase.metadata.create_all, checkfirst=True)

