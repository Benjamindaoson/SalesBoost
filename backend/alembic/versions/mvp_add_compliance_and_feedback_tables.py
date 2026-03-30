"""MVP: Add compliance_logs and session_feedbacks tables

Revision ID: mvp_compliance_feedback
Revises: 4bc7175fd999
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'mvp_compliance_feedback'
down_revision = '4bc7175fd999'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建合规日志表
    op.create_table(
        'compliance_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('turn_number', sa.Integer(), nullable=False),
        sa.Column('original', sa.Text(), nullable=False),
        sa.Column('rewrite', sa.Text(), nullable=True),
        sa.Column('risk_tags', sa.JSON(), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    )
    op.create_index(op.f('ix_compliance_logs_session_id'), 'compliance_logs', ['session_id'], unique=False)
    
    # 创建会话反馈表
    op.create_table(
        'session_feedbacks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('feedback_items', sa.JSON(), nullable=False),
        sa.Column('total_turns', sa.Integer(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.UniqueConstraint('session_id'),
    )
    op.create_index(op.f('ix_session_feedbacks_session_id'), 'session_feedbacks', ['session_id'], unique=True)
    
    # 扩展 messages 表，添加 suggested_reply 字段
    op.add_column('messages', sa.Column('suggested_reply', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('messages', 'suggested_reply')
    op.drop_index(op.f('ix_session_feedbacks_session_id'), table_name='session_feedbacks')
    op.drop_table('session_feedbacks')
    op.drop_index(op.f('ix_compliance_logs_session_id'), table_name='compliance_logs')
    op.drop_table('compliance_logs')

