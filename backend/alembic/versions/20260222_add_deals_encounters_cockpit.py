"""add deals encounters cockpit_events

Revision ID: 20260222_deals
Revises: 540c9902617e
Create Date: 2026-02-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260222_deals'
down_revision: Union[str, Sequence[str], None] = '540c9902617e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'deals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('customer_name', sa.String(200), nullable=False),
        sa.Column('customer_company', sa.String(200), nullable=True),
        sa.Column('customer_title', sa.String(200), nullable=True),
        sa.Column('customer_info', sa.Text(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('stage', sa.String(50), nullable=False),
        sa.Column('expected_close_date', sa.DateTime(), nullable=True),
        sa.Column('close_reason', sa.Text(), nullable=True),
        sa.Column('methodology_framework', sa.String(50), nullable=True),
        sa.Column('methodology_state', sa.Text(), nullable=True),
        sa.Column('methodology_score', sa.Float(), nullable=True),
        sa.Column('deal_metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_deals_owner_stage', 'deals', ['owner_id', 'stage'], unique=False)
    op.create_index('ix_deals_tenant_stage', 'deals', ['tenant_id', 'stage'], unique=False)
    op.create_index('ix_deals_tenant_id', 'deals', ['tenant_id'], unique=False)
    op.create_index('ix_deals_owner_id', 'deals', ['owner_id'], unique=False)

    op.create_table(
        'encounters',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('deal_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('encounter_type', sa.String(20), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('methodology_before', sa.Text(), nullable=True),
        sa.Column('methodology_after', sa.Text(), nullable=True),
        sa.Column('action_items', sa.Text(), nullable=True),
        sa.Column('encounter_metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_encounters_deal_id', 'encounters', ['deal_id'], unique=False)
    op.create_index('ix_encounters_session_id', 'encounters', ['session_id'], unique=False)

    op.create_table(
        'cockpit_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('deal_id', sa.Integer(), nullable=True),
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cockpit_events_tenant_id', 'cockpit_events', ['tenant_id'], unique=False)
    op.create_index('ix_cockpit_events_event_type', 'cockpit_events', ['event_type'], unique=False)
    op.create_index('ix_cockpit_events_deal_id', 'cockpit_events', ['deal_id'], unique=False)


def downgrade() -> None:
    op.drop_table('cockpit_events')
    op.drop_table('encounters')
    op.drop_table('deals')
