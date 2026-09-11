"""Add copilot_state on events and extra on chat_messages."""

from alembic import op
from sqlalchemy import text

revision = "002_copilot_state"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = __import__("sqlalchemy").inspect(bind)
    tables = set(insp.get_table_names())
    if "events" in tables:
        cols = {c["name"] for c in insp.get_columns("events")}
        if "copilot_state" not in cols:
            op.execute(text("ALTER TABLE events ADD COLUMN copilot_state JSON"))
    if "chat_messages" in tables:
        cols = {c["name"] for c in insp.get_columns("chat_messages")}
        if "extra" not in cols:
            op.execute(text("ALTER TABLE chat_messages ADD COLUMN extra JSON"))


def downgrade() -> None:
    pass
