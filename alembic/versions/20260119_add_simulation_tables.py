"""add simulation tables

Revision ID: 20260119_simulation
Revises: 4bc7175fd999
Create Date: 2026-01-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260119_simulation'
down_revision = '4bc7175fd999'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 simulation_runs 表
    op.create_table(
        'simulation_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('scenario_id', sa.String(100), nullable=False, index=True),
        sa.Column('agent_config', sa.JSON(), nullable=False),
        sa.Column('num_trajectories', sa.Integer(), nullable=False),
        sa.Column('seed', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, index=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('avg_goal_completion', sa.Float(), nullable=True),
        sa.Column('avg_trajectory_length', sa.Float(), nullable=True),
        sa.Column('consistency_score', sa.Float(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # 创建 simulation_trajectories 表
    op.create_table(
        'simulation_trajectories',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), nullable=False, index=True),
        sa.Column('scenario_id', sa.String(100), nullable=False, index=True),
        sa.Column('trajectory_index', sa.Integer(), nullable=False),
        sa.Column('seed', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('goal_achieved', sa.Boolean(), nullable=False, default=False),
        sa.Column('total_steps', sa.Integer(), nullable=False, default=0),
        sa.Column('final_stage', sa.String(50), nullable=True),
        sa.Column('final_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('total_reward', sa.Float(), nullable=False, default=0.0),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=False, default=0.0),
        sa.Column('steps_json', sa.JSON(), nullable=True),
        sa.Column('metrics_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # 创建 trajectory_step_records 表
    op.create_table(
        'trajectory_step_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('trajectory_id', sa.String(36), nullable=False, index=True),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('action_content', sa.Text(), nullable=False),
        sa.Column('customer_response', sa.Text(), nullable=False),
        sa.Column('customer_mood', sa.Float(), nullable=False),
        sa.Column('customer_interest', sa.Float(), nullable=False),
        sa.Column('step_reward', sa.Float(), nullable=False, default=0.0),
        sa.Column('step_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('details_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # 创建 preference_pairs 表
    op.create_table(
        'preference_pairs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), nullable=False, index=True),
        sa.Column('scenario_id', sa.String(100), nullable=False, index=True),
        sa.Column('chosen_trajectory_id', sa.String(36), nullable=False),
        sa.Column('rejected_trajectory_id', sa.String(36), nullable=False),
        sa.Column('context', sa.Text(), nullable=False),
        sa.Column('chosen_response', sa.Text(), nullable=False),
        sa.Column('rejected_response', sa.Text(), nullable=False),
        sa.Column('score_delta', sa.Float(), nullable=False),
        sa.Column('quality_delta', sa.Float(), nullable=False),
        sa.Column('preference_reason', sa.Text(), nullable=False),
        sa.Column('preference_dimensions', sa.JSON(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # 创建 sft_samples 表
    op.create_table(
        'sft_samples',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('trajectory_id', sa.String(36), nullable=False, index=True),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('context', sa.Text(), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=False),
        sa.Column('is_positive_example', sa.Boolean(), nullable=False),
        sa.Column('annotator', sa.String(50), nullable=False, default='auto'),
        sa.Column('annotation_confidence', sa.Float(), nullable=False, default=1.0),
        sa.Column('tags_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    # 删除表（按相反顺序）
    op.drop_table('sft_samples')
    op.drop_table('preference_pairs')
    op.drop_table('trajectory_step_records')
    op.drop_table('simulation_trajectories')
    op.drop_table('simulation_runs')





