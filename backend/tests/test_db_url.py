from app.core.db import normalize_database_url


def test_normalize_neon_postgres_url():
    dsn, args = normalize_database_url(
        "postgres://user:pass@ep-foo.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    )
    assert dsn.startswith("postgresql+asyncpg://")
    assert "sslmode" not in dsn
    assert args.get("ssl") is True


def test_normalize_pooler_disables_statement_cache():
    dsn, args = normalize_database_url(
        "postgresql://user:pass@ep-foo-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
    )
    assert "postgresql+asyncpg://" in dsn
    assert args.get("statement_cache_size") == 0
