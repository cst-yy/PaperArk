"""Shared PostgreSQL fixtures for backend integration tests."""

import os

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
import app.models  # noqa: F401 - register all declarative models


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """Yield a clean database backed by PostgreSQL and pgvector.

    TEST_DATABASE_URL must point to an isolated disposable database. Tests never
    use the application database configured by DATABASE_URL.
    """
    database_url = os.environ["TEST_DATABASE_URL"]
    engine = create_async_engine(database_url)

    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db

    await engine.dispose()
