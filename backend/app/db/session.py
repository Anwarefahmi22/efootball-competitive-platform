from collections.abc import AsyncGenerator
from ssl import create_default_context

from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def create_db_engine(database_url: str, **engine_kwargs):
    """Create the async engine, translating a URL `sslmode` query param
    (how Neon and other hosted Postgres providers hand out connection
    strings) into asyncpg's `ssl` connect argument."""
    url = make_url(database_url)
    query = dict(url.query)
    mode = query.pop("sslmode", None)
    if mode is not None:
        url = url.set(query=query)
        if mode == "disable":
            engine_kwargs.setdefault("connect_args", {})["ssl"] = False
        elif mode in ("verify-ca", "verify-full"):
            engine_kwargs.setdefault("connect_args", {})["ssl"] = create_default_context()
        else:  # prefer / require
            engine_kwargs.setdefault("connect_args", {})["ssl"] = True
    return create_async_engine(url, **engine_kwargs)


engine = create_db_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
