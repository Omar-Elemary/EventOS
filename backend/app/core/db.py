from collections.abc import AsyncGenerator
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID
import json
import os
import ssl

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

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


def _ssl_arg(host: str, sslmode: str):
    hosted = "neon.tech" in host or "supabase.co" in host or "supabase.com" in host
    if sslmode not in {"require", "verify-ca", "verify-full", "prefer"} and not hosted:
        return None
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    # Supabase pooler cert chains fail verify on some serverless CA stores (Vercel).
    if "supabase.co" in host or "supabase.com" in host:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def normalize_database_url(url: str) -> tuple[str, dict]:
    """Turn Neon/Vercel/Supabase postgres:// URLs into SQLAlchemy asyncpg DSNs."""
    raw = (url or "").strip()
    if not raw:
        return raw, {}
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    if raw.startswith("postgresql://") and "+asyncpg" not in raw.split("://", 1)[0]:
        raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]
    parts = urlsplit(raw)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    connect_args: dict = {}
    sslmode = (query.pop("sslmode", None) or "").lower()
    query.pop("channel_binding", None)
    host = parts.hostname or ""
    ssl_arg = _ssl_arg(host, sslmode)
    if ssl_arg is not None:
        connect_args["ssl"] = ssl_arg
    if "pooler" in host or query.get("pgbouncer") == "true":
        connect_args["statement_cache_size"] = 0
    dsn = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return dsn, connect_args


def init_engine(url: str | None = None, *, echo: bool = False):
    global engine, SessionLocal
    dsn, connect_args = normalize_database_url(url or get_settings().database_url)
    kwargs: dict = {
        "echo": echo,
        "future": True,
        "json_serializer": json_dumps,
        "pool_pre_ping": True,
    }
    if connect_args:
        kwargs["connect_args"] = connect_args
    if "sqlite" not in dsn:
        if os.getenv("VERCEL"):
            kwargs["poolclass"] = NullPool
        else:
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
