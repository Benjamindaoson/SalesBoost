"""merge_2026_and_mvp

Revision ID: ae95c5f52691
Revises: 20260119_simulation, mvp_compliance_feedback
Create Date: 2026-01-23 16:19:26.431597

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae95c5f52691'
down_revision: Union[str, Sequence[str], None] = ('20260119_simulation', 'mvp_compliance_feedback')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
