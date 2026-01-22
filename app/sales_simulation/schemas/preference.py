"""
偏好数据 Schema
定义用于 Post-training 的偏好数据结构
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PreferencePair(BaseModel):
    """偏好对（用于 DPO / RLHF）"""
    id: str = Field(..., description="偏好对 ID")
    run_id: str = Field(..., description="运行 ID")
    scenario_id: str = Field(..., description="场景 ID")
    
    # 偏好对
    chosen_trajectory_id: str = Field(..., description="更优轨迹 ID")
    rejected_trajectory_id: str = Field(..., description="较差轨迹 ID")
    
    # 上下文
    context: str = Field(..., description="共同上下文")
    
    # 对比数据
    chosen_response: str = Field(..., description="更优响应")
    rejected_response: str = Field(..., description="较差响应")
    
    # 质量差异
    score_delta: float = Field(..., description="得分差异")
    quality_delta: float = Field(..., ge=0.0, description="质量差异")
    
    # 偏好原因
    preference_reason: str = Field(..., description="偏好原因")
    preference_dimensions: Dict[str, float] = Field(..., description="各维度偏好差异")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "pref_001",
                "run_id": "run_001",
                "scenario_id": "scenario_001",
                "chosen_trajectory_id": "traj_001",
                "rejected_trajectory_id": "traj_002",
                "context": "客户表达了对价格的担忧",
                "chosen_response": "我理解您的顾虑。让我们先看看产品能为您带来的价值...",
                "rejected_response": "我们的价格已经很优惠了，您可以考虑一下",
                "score_delta": 0.25,
                "quality_delta": 0.30,
                "preference_reason": "更优响应展现了同理心和价值导向",
                "preference_dimensions": {
                    "empathy": 0.4,
                    "value_focus": 0.3,
                    "professionalism": 0.2
                }
            }
        }


class SFTSample(BaseModel):
    """SFT 训练样本（监督微调）"""
    id: str = Field(..., description="样本 ID")
    trajectory_id: str = Field(..., description="轨迹 ID")
    step_index: int = Field(..., ge=0, description="步骤索引")
    
    # 训练数据
    context: str = Field(..., description="上下文（对话历史 + 当前状态）")
    action: str = Field(..., description="目标动作（Agent 应该采取的行动）")
    reasoning: Optional[str] = Field(None, description="推理过程")
    
    # 质量标签
    quality_score: float = Field(..., ge=0.0, le=1.0, description="质量评分")
    is_positive_example: bool = Field(..., description="是否为正例")
    
    # 标注信息
    annotator: str = Field(default="auto", description="标注者：auto/human")
    annotation_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="标注置信度")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    tags: List[str] = Field(default_factory=list, description="标签")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "sft_001",
                "trajectory_id": "traj_001",
                "step_index": 5,
                "context": "客户：我们预算有限...\n历史：[3轮对话]",
                "action": "我理解预算是重要考量。让我们先聚焦在您最关心的痛点上...",
                "reasoning": "展现同理心，引导回价值讨论",
                "quality_score": 0.92,
                "is_positive_example": True,
                "annotator": "auto",
                "annotation_confidence": 0.95,
                "tags": ["objection_handling", "budget_concern", "high_quality"]
            }
        }


class GRPOSample(BaseModel):
    """GRPO 训练样本（Group Relative Policy Optimization）"""
    id: str = Field(..., description="样本 ID")
    run_id: str = Field(..., description="运行 ID")
    scenario_id: str = Field(..., description="场景 ID")
    
    # 上下文
    context: str = Field(..., description="共同上下文")
    
    # 候选响应组
    responses: List[Dict[str, Any]] = Field(..., description="候选响应列表")
    
    # 相对排序
    ranking: List[int] = Field(..., description="相对排序（索引列表）")
    scores: List[float] = Field(..., description="对应得分")
    
    # 奖励信号
    rewards: List[float] = Field(..., description="奖励列表")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "grpo_001",
                "run_id": "run_001",
                "scenario_id": "scenario_001",
                "context": "客户表达了价格担忧",
                "responses": [
                    {"text": "我理解您的顾虑...", "trajectory_id": "traj_001"},
                    {"text": "价格很优惠了", "trajectory_id": "traj_002"},
                    {"text": "让我们看看ROI...", "trajectory_id": "traj_003"}
                ],
                "ranking": [0, 2, 1],
                "scores": [0.92, 0.85, 0.65],
                "rewards": [1.0, 0.5, -0.2]
            }
        }





