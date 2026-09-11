"""Event State tables, versioning, provenance, and canonical research records."""

from alembic import op
from sqlalchemy import inspect, text

revision = "004_event_state"
down_revision = "003_research_records"
branch_labels = None
depends_on = None


def _add(table: str, name: str, ddl: str) -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if table not in set(insp.get_table_names()):
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    if name in cols:
        return
    op.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def upgrade() -> None:
    for name, ddl in {
        "updated_at": "DATETIME",
        "archived_at": "DATETIME",
        "deadline": "DATETIME",
        "description": "TEXT",
        "objectives": "JSON",
        "tags": "JSON",
        "data_mode": "VARCHAR(16)",
        "event_state_version": "INTEGER",
    }.items():
        _add("events", name, ddl)
    _add("budgets", "committed", "FLOAT")
    _add("budgets", "estimated", "FLOAT")
    for name, ddl in {
        "status": "VARCHAR(32)",
        "vendor_name": "VARCHAR(255)",
        "due_date": "VARCHAR(32)",
        "deposit": "FLOAT",
    }.items():
        _add("budget_items", name, ddl)
    for name, ddl in {
        "start_time": "DATETIME",
        "end_time": "DATETIME",
        "depends_on": "JSON",
        "owner": "VARCHAR(255)",
        "phase": "VARCHAR(32)",
    }.items():
        _add("tasks", name, ddl)
    for name, ddl in {
        "score": "FLOAT",
        "owner": "VARCHAR(255)",
        "status": "VARCHAR(32)",
        "trigger": "TEXT",
        "ai_recommendation": "TEXT",
    }.items():
        _add("risks", name, ddl)
    _add("simulations", "base_version", "INTEGER")
    _add("simulations", "status", "VARCHAR(32)")
    for table in ("venues", "vendors"):
        for name, ddl in {
            "source_url": "VARCHAR(512)",
            "source_tier": "VARCHAR(32)",
            "confidence": "FLOAT",
            "last_checked_at": "DATETIME",
            "price_type": "VARCHAR(32)",
            "requires_quote": "BOOLEAN",
            "provider": "VARCHAR(32)",
        }.items():
            _add(table, name, ddl)
    for name, ddl in {
        "normalized_query": "TEXT",
        "source_url": "VARCHAR(512)",
        "source_tier": "VARCHAR(32)",
        "title": "VARCHAR(512)",
        "extracted_data": "JSON",
        "retrieved_at": "DATETIME",
        "confidence": "FLOAT",
        "provider": "VARCHAR(32)",
        "raw_reference": "TEXT",
    }.items():
        _add("research_records", name, ddl)

    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())
    dialect = bind.dialect.name
    ts = "DATETIME" if dialect == "sqlite" else "TIMESTAMPTZ"

    if "activity_log" not in tables:
        op.execute(
            text(
                f"""
                CREATE TABLE activity_log (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    event_id VARCHAR(36) NOT NULL,
                    at {ts},
                    actor VARCHAR(64) NOT NULL,
                    action VARCHAR(64) NOT NULL,
                    summary TEXT DEFAULT '',
                    payload JSON,
                    state_version INTEGER DEFAULT 0
                )
                """
            )
        )
    if "decisions" not in tables:
        op.execute(
            text(
                f"""
                CREATE TABLE decisions (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    event_id VARCHAR(36) NOT NULL,
                    problem TEXT NOT NULL,
                    options JSON,
                    consequences JSON,
                    recommendation TEXT DEFAULT '',
                    status VARCHAR(32) DEFAULT 'open',
                    chosen_option VARCHAR(128),
                    created_at {ts}
                )
                """
            )
        )
    if "event_venues" not in tables:
        op.execute(
            text(
                f"""
                CREATE TABLE event_venues (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    event_id VARCHAR(36) NOT NULL,
                    venue_id VARCHAR(36),
                    name VARCHAR(255) NOT NULL,
                    location VARCHAR(255) DEFAULT '',
                    capacity INTEGER DEFAULT 0,
                    estimated_cost FLOAT DEFAULT 0,
                    facilities JSON,
                    suitability_score FLOAT DEFAULT 50,
                    pros JSON,
                    cons JSON,
                    status VARCHAR(32) DEFAULT 'considered',
                    notes TEXT DEFAULT '',
                    source_url VARCHAR(512) DEFAULT '',
                    source_tier VARCHAR(32) DEFAULT 'mock',
                    confidence FLOAT DEFAULT 0.7,
                    last_checked_at {ts},
                    price_type VARCHAR(32) DEFAULT 'estimated',
                    requires_quote BOOLEAN DEFAULT 0,
                    provider VARCHAR(32) DEFAULT 'mock',
                    distance_km FLOAT,
                    extra JSON
                )
                """
            )
        )
    if "event_vendors" not in tables:
        op.execute(
            text(
                f"""
                CREATE TABLE event_vendors (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    event_id VARCHAR(36) NOT NULL,
                    vendor_id VARCHAR(36),
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(64) DEFAULT '',
                    location VARCHAR(255) DEFAULT '',
                    estimated_cost FLOAT DEFAULT 0,
                    rating FLOAT DEFAULT 4.0,
                    services JSON,
                    status VARCHAR(32) DEFAULT 'considered',
                    notes TEXT DEFAULT '',
                    quote_status VARCHAR(32) DEFAULT 'none',
                    source_url VARCHAR(512) DEFAULT '',
                    source_tier VARCHAR(32) DEFAULT 'mock',
                    confidence FLOAT DEFAULT 0.7,
                    last_checked_at {ts},
                    price_type VARCHAR(32) DEFAULT 'estimated',
                    requires_quote BOOLEAN DEFAULT 0,
                    provider VARCHAR(32) DEFAULT 'mock'
                )
                """
            )
        )
    if "plan_snapshots" not in tables:
        op.execute(
            text(
                f"""
                CREATE TABLE plan_snapshots (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    event_id VARCHAR(36) NOT NULL,
                    version INTEGER NOT NULL,
                    snapshot JSON,
                    created_at {ts}
                )
                """
            )
        )


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS plan_snapshots"))
    op.execute(text("DROP TABLE IF EXISTS event_vendors"))
    op.execute(text("DROP TABLE IF EXISTS event_venues"))
    op.execute(text("DROP TABLE IF EXISTS decisions"))
    op.execute(text("DROP TABLE IF EXISTS activity_log"))
