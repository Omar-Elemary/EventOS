from sqlalchemy import inspect, text

EVENT_COLUMNS = {
    "updated_at": "DATETIME",
    "archived_at": "DATETIME",
    "deadline": "DATETIME",
    "description": "TEXT",
    "objectives": "JSON",
    "tags": "JSON",
    "data_mode": "VARCHAR(16)",
    "event_state_version": "INTEGER",
}

BUDGET_COLUMNS = {
    "committed": "FLOAT",
    "estimated": "FLOAT",
}

BUDGET_ITEM_COLUMNS = {
    "status": "VARCHAR(32)",
    "vendor_name": "VARCHAR(255)",
    "due_date": "VARCHAR(32)",
    "deposit": "FLOAT",
}

TASK_COLUMNS = {
    "start_time": "DATETIME",
    "end_time": "DATETIME",
    "depends_on": "JSON",
    "owner": "VARCHAR(255)",
    "phase": "VARCHAR(32)",
}

RISK_COLUMNS = {
    "score": "FLOAT",
    "owner": "VARCHAR(255)",
    "status": "VARCHAR(32)",
    "trigger": "TEXT",
    "ai_recommendation": "TEXT",
    "explanation": "TEXT",
    "solutions": "JSON",
}

SIM_COLUMNS = {
    "base_version": "INTEGER",
    "status": "VARCHAR(32)",
}

VENUE_COLUMNS = {
    "source_url": "VARCHAR(512)",
    "source_tier": "VARCHAR(32)",
    "confidence": "FLOAT",
    "last_checked_at": "DATETIME",
    "price_type": "VARCHAR(32)",
    "requires_quote": "BOOLEAN",
    "provider": "VARCHAR(32)",
}

VENDOR_COLUMNS = {
    "source_url": "VARCHAR(512)",
    "source_tier": "VARCHAR(32)",
    "confidence": "FLOAT",
    "last_checked_at": "DATETIME",
    "price_type": "VARCHAR(32)",
    "requires_quote": "BOOLEAN",
    "provider": "VARCHAR(32)",
}

RESEARCH_COLUMNS = {
    "normalized_query": "TEXT",
    "source_url": "VARCHAR(512)",
    "source_tier": "VARCHAR(32)",
    "title": "VARCHAR(512)",
    "extracted_data": "JSON",
    "retrieved_at": "DATETIME",
    "confidence": "FLOAT",
    "provider": "VARCHAR(32)",
    "raw_reference": "TEXT",
}


def _add_columns(sync_conn, table: str, columns: dict[str, str]) -> None:
    insp = inspect(sync_conn)
    if table not in set(insp.get_table_names()):
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    for name, ddl in columns.items():
        if name in existing:
            continue
        sync_conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


USER_COLUMNS = {
    "password_hash": "VARCHAR(255)",
}


def ensure_event_state_columns(sync_conn) -> None:
    _add_columns(sync_conn, "users", USER_COLUMNS)
    _add_columns(sync_conn, "events", EVENT_COLUMNS)
    _add_columns(sync_conn, "budgets", BUDGET_COLUMNS)
    _add_columns(sync_conn, "budget_items", BUDGET_ITEM_COLUMNS)
    _add_columns(sync_conn, "tasks", TASK_COLUMNS)
    _add_columns(sync_conn, "risks", RISK_COLUMNS)
    _add_columns(sync_conn, "simulations", SIM_COLUMNS)
    _add_columns(sync_conn, "venues", VENUE_COLUMNS)
    _add_columns(sync_conn, "vendors", VENDOR_COLUMNS)
    _add_columns(sync_conn, "research_records", RESEARCH_COLUMNS)
    insp = inspect(sync_conn)
    tables = set(insp.get_table_names())
    if "events" in tables:
        cols = {c["name"] for c in insp.get_columns("events")}
        if "copilot_state" not in cols:
            sync_conn.execute(text("ALTER TABLE events ADD COLUMN copilot_state JSON"))
    if "chat_messages" in tables:
        cols = {c["name"] for c in insp.get_columns("chat_messages")}
        if "extra" not in cols:
            sync_conn.execute(text("ALTER TABLE chat_messages ADD COLUMN extra JSON"))
