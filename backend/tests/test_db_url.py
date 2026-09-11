import ssl

from app.core.db import normalize_database_url


def test_normalize_neon_postgres_url():
    dsn, args = normalize_database_url(
        "postgres://user:pass@ep-foo.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    )
    assert dsn.startswith("postgresql+asyncpg://")
    assert "sslmode" not in dsn
    assert isinstance(args.get("ssl"), ssl.SSLContext)
    assert args["ssl"].verify_mode == ssl.CERT_REQUIRED


def test_normalize_pooler_disables_statement_cache():
    dsn, args = normalize_database_url(
        "postgresql://user:pass@ep-foo-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
    )
    assert "postgresql+asyncpg://" in dsn
    assert args.get("statement_cache_size") == 0


def test_normalize_supabase_pooler_url():
    dsn, args = normalize_database_url(
        "postgresql://eventos.abc:pass@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require"
    )
    assert dsn.startswith("postgresql+asyncpg://")
    assert "sslmode" not in dsn
    assert isinstance(args.get("ssl"), ssl.SSLContext)
    assert args["ssl"].verify_mode == ssl.CERT_NONE
    assert args.get("statement_cache_size") == 0
