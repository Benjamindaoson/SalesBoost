"""add turn_id and status to messages

Revision ID: 20260127_add_message_turn_status
Revises: 20260126_context_snapshot
Create Date: 2026-01-27 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260127_add_message_turn_status"
down_revision: Union[str, Sequence[str], None] = "20260126_context_snapshot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("turn_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'committed'"),
        ),
    )
    op.create_index("ix_messages_turn_id", "messages", ["turn_id"])
    op.create_index("ix_messages_status", "messages", ["status"])


def downgrade() -> None:
    op.drop_index("ix_messages_status", table_name="messages")
    op.drop_index("ix_messages_turn_id", table_name="messages")
    op.drop_column("messages", "status")
    op.drop_column("messages", "turn_id")
