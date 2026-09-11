from collections.abc import AsyncGenerator
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID
import json

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = None


def json_default(o: Any) -> Any:
    if isinstance(o, datetime):
        return o.isoformat()
    if isinstance(o, date):
        return o.isoformat()
    if isinstance(o, Enum):
        return o.value
    if isinstance(o, UUID):
        return str(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")


def json_dumps(value: Any) -> str:
    return json.dumps(value, default=json_default)


def json_safe(value: Any) -> Any:
    return json.loads(json_dumps(value))


def init_engine(url: str | None = None, *, echo: bool = False):
    global engine, SessionLocal
    dsn = url or get_settings().database_url
    kwargs: dict = {
        "echo": echo,
        "future": True,
        "json_serializer": json_dumps,
        "pool_pre_ping": True,
    }
    if "sqlite" not in dsn:
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
    engine = create_async_engine(dsn, **kwargs)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine


def session_maker() -> async_sessionmaker[AsyncSession]:
    global SessionLocal
    if SessionLocal is None:
        init_engine()
    assert SessionLocal is not None
    return SessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_maker()() as session:
        yield session
