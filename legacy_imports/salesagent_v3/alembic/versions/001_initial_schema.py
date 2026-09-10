"""Initial schema with LangGraph checkpoints table

Revision ID: 001
Revises:
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('customer_id', sa.String(100), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('current_stage', sa.String(20), nullable=False, server_default='ICEBREAK'),
        sa.Column('stage_history', postgresql.JSONB, nullable=True),
        sa.Column('is_waiting_approval', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('pending_human_override', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('idx_sessions_customer_id', 'sessions', ['customer_id'])
    op.create_index('idx_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('idx_sessions_status', 'sessions', ['status'])

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('turn_index', sa.Integer, nullable=False),
        sa.Column('reasoning_output', postgresql.JSONB, nullable=True),
        sa.Column('guard_events', postgresql.JSONB, nullable=True),
        sa.Column('model_used', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('idx_messages_session_id', 'messages', ['session_id'])
    op.create_index('idx_messages_created_at', 'messages', ['created_at'])

    # Create adaptive_memory table
    op.create_table(
        'adaptive_memory',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_key', sa.String(100), nullable=False),
        sa.Column('entity_value', sa.Text, nullable=False),
        sa.Column('confidence', sa.Float, nullable=False, server_default='1.0'),
        sa.Column('source_turn', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('idx_adaptive_memory_session_id', 'adaptive_memory', ['session_id'])
    op.create_index('idx_adaptive_memory_entity_key', 'adaptive_memory', ['entity_key'])

    # Create prompt_templates table
    op.create_table(
        'prompt_templates',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('version', sa.Integer, nullable=False),
        sa.Column('template', sa.Text, nullable=False),
        sa.Column('variables', postgresql.JSONB, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('traffic_weight', sa.Float, nullable=False, server_default='1.0'),
        sa.Column('avg_reward', sa.Float, nullable=True),
        sa.Column('eval_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('idx_prompt_templates_name_version', 'prompt_templates', ['name', 'version'], unique=True)
    op.create_index('idx_prompt_templates_status', 'prompt_templates', ['status'])

    # Create knowledge_chunks table
    op.create_table(
        'knowledge_chunks',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('document_id', sa.String(100), nullable=False),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('idx_knowledge_chunks_user_id', 'knowledge_chunks', ['user_id'])
    op.create_index('idx_knowledge_chunks_document_id', 'knowledge_chunks', ['document_id'])

    # Create langgraph_checkpoints table (NEW - critical for HITL)
    op.create_table(
        'langgraph_checkpoints',
        sa.Column('checkpoint_id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('thread_id', sa.String(100), nullable=False, unique=True),
        sa.Column('checkpoint_data', sa.LargeBinary, nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('idx_langgraph_checkpoints_thread_id', 'langgraph_checkpoints', ['thread_id'])
    op.create_index('idx_langgraph_checkpoints_updated_at', 'langgraph_checkpoints', ['updated_at'])


def downgrade() -> None:
    op.drop_table('langgraph_checkpoints')
    op.drop_table('knowledge_chunks')
    op.drop_table('prompt_templates')
    op.drop_table('adaptive_memory')
    op.drop_table('messages')
    op.drop_table('sessions')
