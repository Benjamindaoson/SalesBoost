"""
轨迹记录 Schema
定义模拟运行过程中的轨迹数据结构
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ActionType(str, Enum):
    """动作类型"""
    SPEAK = "speak"                  # 说话
    LISTEN = "listen"                # 倾听
    QUESTION = "question"            # 提问
    PRESENT = "present"              # 展示
    HANDLE_OBJECTION = "handle_objection"  # 处理异议
    CLOSE = "close"                  # 促单
    END = "end"                      # 结束


class StepAction(BaseModel):
    """单步动作"""
    action_type: ActionType = Field(..., description="动作类型")
    content: str = Field(..., description="动作内容（如话术）")
    reasoning: Optional[str] = Field(None, description="推理过程")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    
    # 元数据
    agent_id: Optional[str] = Field(None, description="执行 Agent ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")
    
    class Config:
        json_schema_extra = {
            "example": {
                "action_type": "question",
                "content": "李总，您目前团队在协作上遇到的最大挑战是什么？",
                "reasoning": "通过开放式提问挖掘客户痛点",
                "confidence": 0.9,
                "agent_id": "dialogue_agent_1"
            }
        }


class StepObservation(BaseModel):
    """单步观察"""
    customer_response: str = Field(..., description="客户回应")
    customer_mood: float = Field(..., ge=0.0, le=1.0, description="客户情绪值")
    customer_interest: float = Field(..., ge=0.0, le=1.0, description="客户兴趣度")
    
    # 状态信息
    current_stage: str = Field(..., description="当前销售阶段")
    goal_progress: float = Field(default=0.0, ge=0.0, le=1.0, description="目标进度")
    
    # 检测结果
    compliance_passed: bool = Field(default=True, description="合规检查是否通过")
    detected_signals: List[str] = Field(default_factory=list, description="检测到的信号")
    
    class Config:
        json_schema_extra = {
            "example": {
                "customer_response": "我们现在用的工具确实有点老了，主要问题是不同部门的数据打不通",
                "customer_mood": 0.6,
                "customer_interest": 0.5,
                "current_stage": "NEEDS_DISCOVERY",
                "goal_progress": 0.2,
                "compliance_passed": True,
                "detected_signals": ["pain_point_mentioned", "interest_signal"]
            }
        }


class TrajectoryStep(BaseModel):
    """轨迹单步"""
    step_index: int = Field(..., ge=0, description="步骤索引")
    action: StepAction = Field(..., description="Agent 动作")
    observation: StepObservation = Field(..., description="环境观察")
    
    # 评估
    step_reward: float = Field(default=0.0, description="单步奖励")
    step_score: float = Field(default=0.0, ge=0.0, le=1.0, description="单步评分")
    
    # 调试信息
    debug_info: Optional[Dict[str, Any]] = Field(None, description="调试信息")


class TrajectoryStatus(str, Enum):
    """轨迹状态"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    TERMINATED = "terminated"


class Trajectory(BaseModel):
    """完整轨迹"""
    id: str = Field(..., description="轨迹唯一标识")
    run_id: str = Field(..., description="所属运行 ID")
    scenario_id: str = Field(..., description="场景 ID")
    
    # 配置
    seed: int = Field(..., description="随机种子")
    agent_config: Dict[str, Any] = Field(..., description="Agent 配置")
    
    # 轨迹数据
    steps: List[TrajectoryStep] = Field(default_factory=list, description="步骤列表")
    
    # 结果
    status: TrajectoryStatus = Field(default=TrajectoryStatus.RUNNING, description="状态")
    goal_achieved: bool = Field(default=False, description="目标是否达成")
    final_score: float = Field(default=0.0, ge=0.0, le=1.0, description="最终得分")
    total_reward: float = Field(default=0.0, description="总奖励")
    
    # 统计
    total_steps: int = Field(default=0, description="总步数")
    duration_seconds: float = Field(default=0.0, description="持续时间（秒）")
    
    # 时间戳
    started_at: datetime = Field(default_factory=datetime.utcnow, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "traj_001",
                "run_id": "run_001",
                "scenario_id": "scenario_001",
                "seed": 42,
                "agent_config": {"type": "single", "model": "gpt-4"},
                "status": "completed",
                "goal_achieved": True,
                "final_score": 0.85,
                "total_steps": 12
            }
        }




