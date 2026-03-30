"""add mt_courses and mt_sessions for multi-tenant schema

Revision ID: 20260222_mt
Revises: 20260222_deals
Create Date: 2026-02-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260222_mt"
down_revision: Union[str, Sequence[str], None] = '20260222_deals'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mt_courses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), nullable=True, index=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("product_category", sa.String(100), nullable=True),
        sa.Column("difficulty_level", sa.String(20), nullable=False),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("prerequisites", sa.Text(), nullable=True),
        sa.Column("learning_objectives", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "mt_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), nullable=True, index=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("course_id", sa.String(36), nullable=False, index=True),
        sa.Column("scenario_id", sa.String(36), nullable=False, index=True),
        sa.Column("persona_id", sa.String(36), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(), nullable=False),
        sa.Column("total_turns", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("final_stage", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("mt_sessions")
    op.drop_table("mt_courses")
