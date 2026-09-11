"""Research cache table for venues, vendors, weather, FX, and web notes."""

from alembic import op
from sqlalchemy import inspect, text

revision = "003_research_records"
down_revision = "002_copilot_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "research_records" in set(insp.get_table_names()):
        return
    dialect = bind.dialect.name
    if dialect == "sqlite":
        op.execute(
            text(
                """
                CREATE TABLE research_records (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    query_key VARCHAR(64) NOT NULL UNIQUE,
                    event_id VARCHAR(36),
                    kind VARCHAR(32) NOT NULL,
                    query TEXT DEFAULT '',
                    payload JSON,
                    source_type VARCHAR(32) DEFAULT 'mock',
                    fingerprint VARCHAR(64) DEFAULT '',
                    fetched_at DATETIME,
                    expires_at DATETIME
                )
                """
            )
        )
    else:
        op.execute(
            text(
                """
                CREATE TABLE research_records (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    query_key VARCHAR(64) NOT NULL UNIQUE,
                    event_id VARCHAR(36) REFERENCES events(id),
                    kind VARCHAR(32) NOT NULL,
                    query TEXT DEFAULT '',
                    payload JSON,
                    source_type VARCHAR(32) DEFAULT 'mock',
                    fingerprint VARCHAR(64) DEFAULT '',
                    fetched_at TIMESTAMPTZ,
                    expires_at TIMESTAMPTZ
                )
                """
            )
        )
    op.execute(text("CREATE INDEX IF NOT EXISTS ix_research_records_query_key ON research_records (query_key)"))


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS research_records"))
