"""add_is_rag_hit_to_messages

Revision ID: 540c9902617e
Revises: ae95c5f52691
Create Date: 2026-01-23 16:19:38.651764

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '540c9902617e'
down_revision: Union[str, Sequence[str], None] = 'ae95c5f52691'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
