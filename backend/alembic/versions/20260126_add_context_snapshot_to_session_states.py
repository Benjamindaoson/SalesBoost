"""add context_snapshot to session_states

Revision ID: 20260126_context_snapshot
Revises: 540c9902617e
Create Date: 2026-01-26 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260126_context_snapshot"
down_revision: Union[str, Sequence[str], None] = "540c9902617e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_states",
        sa.Column(
            "context_snapshot",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("session_states", "context_snapshot")

