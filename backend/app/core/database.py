import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_current_user_id() -> uuid.UUID:
    """FastAPI dependency: returns the current user's ID.

    In P0 single-user mode this is a constant. When real auth is added,
    replace the body with a JWT-decode dependency — every endpoint that
    uses Depends(get_current_user_id) will automatically pick it up.
    """
    return DEFAULT_USER_ID


async def init_db() -> None:
    """Seed the default local user after Alembic has upgraded the schema.

    Schema creation and evolution are owned exclusively by Alembic. The
    container entrypoint runs ``alembic upgrade head`` before FastAPI starts.
    """
    from app.models import User

    # Seed default user
    async with async_session_factory() as session:
        existing = await session.execute(
            select(User).where(User.id == DEFAULT_USER_ID)
        )
        if not existing.scalars().first():
            session.add(User(
                id=DEFAULT_USER_ID,
                username="researcher",
                email="researcher@local",
                password_hash="",
            ))
            await session.commit()
