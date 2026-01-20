"""
模拟运行数据库模型
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Float, Boolean, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SimulationRun(Base, TimestampMixin):
    """模拟运行记录"""
    __tablename__ = "simulation_runs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # 配置
    agent_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    num_trajectories: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 状态
    status: Mapped[str] = mapped_column(
        String(20),
        default="running",
        index=True,
    )  # running / completed / failed
    
    # 时间
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 聚合指标
    avg_goal_completion: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_trajectory_length: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    consistency_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 元数据
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class SimulationTrajectory(Base, TimestampMixin):
    """模拟轨迹记录"""
    __tablename__ = "simulation_trajectories"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # 配置
    trajectory_index: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 结果
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    goal_achieved: Mapped[bool] = mapped_column(Boolean, default=False)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    final_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    final_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_reward: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 时间
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 详细数据（JSON 存储）
    steps_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    metrics_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class TrajectoryStepRecord(Base, TimestampMixin):
    """轨迹步骤记录（可选，用于详细分析）"""
    __tablename__ = "trajectory_step_records"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trajectory_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 动作
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action_content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 观察
    customer_response: Mapped[str] = mapped_column(Text, nullable=False)
    customer_mood: Mapped[float] = mapped_column(Float, nullable=False)
    customer_interest: Mapped[float] = mapped_column(Float, nullable=False)
    
    # 评估
    step_reward: Mapped[float] = mapped_column(Float, default=0.0)
    step_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 详细数据
    details_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)




