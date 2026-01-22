"""
场景定义 Schema
定义销售任务模拟场景的结构
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class DifficultyLevel(str, Enum):
    """难度等级"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class CustomerType(str, Enum):
    """客户类型"""
    COLD_LEAD = "cold_lead"              # 冷线索
    WARM_LEAD = "warm_lead"              # 温线索
    HOT_LEAD = "hot_lead"                # 热线索
    EXISTING_CUSTOMER = "existing_customer"  # 老客户
    CHURNED_CUSTOMER = "churned_customer"    # 流失客户


class SalesGoal(BaseModel):
    """销售目标"""
    goal_type: str = Field(..., description="目标类型：appointment/demo/trial/purchase/upsell")
    target_value: Optional[float] = Field(None, description="目标值（如金额）")
    success_criteria: List[str] = Field(..., description="成功标准列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "goal_type": "demo",
                "target_value": None,
                "success_criteria": [
                    "客户同意参加产品演示",
                    "确认具体时间和参与人员",
                    "发送日历邀请"
                ]
            }
        }


class CustomerProfile(BaseModel):
    """客户画像"""
    name: str = Field(..., description="客户姓名")
    company: Optional[str] = Field(None, description="公司名称")
    role: str = Field(..., description="职位角色")
    customer_type: CustomerType = Field(..., description="客户类型")
    
    # 心理特征
    personality_traits: List[str] = Field(default_factory=list, description="性格特征")
    pain_points: List[str] = Field(default_factory=list, description="痛点列表")
    objections: List[str] = Field(default_factory=list, description="常见异议")
    
    # 决策特征
    decision_style: str = Field(default="analytical", description="决策风格：analytical/emotional/collaborative")
    budget_sensitivity: float = Field(default=0.5, ge=0.0, le=1.0, description="价格敏感度")
    urgency_level: float = Field(default=0.5, ge=0.0, le=1.0, description="紧迫程度")
    
    # 初始状态
    initial_mood: float = Field(default=0.5, ge=0.0, le=1.0, description="初始情绪值")
    initial_interest: float = Field(default=0.3, ge=0.0, le=1.0, description="初始兴趣度")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "李明",
                "company": "某科技公司",
                "role": "技术总监",
                "customer_type": "warm_lead",
                "personality_traits": ["理性", "谨慎", "注重细节"],
                "pain_points": ["团队协作效率低", "工具分散", "数据孤岛"],
                "objections": ["价格太贵", "担心学习成本", "已有类似工具"],
                "decision_style": "analytical",
                "budget_sensitivity": 0.7,
                "urgency_level": 0.4,
                "initial_mood": 0.5,
                "initial_interest": 0.4
            }
        }


class ScenarioConfig(BaseModel):
    """场景配置"""
    max_turns: int = Field(default=20, ge=1, le=100, description="最大对话轮数")
    timeout_seconds: int = Field(default=600, ge=60, le=3600, description="超时时间（秒）")
    
    # 环境参数
    enable_interruption: bool = Field(default=True, description="是否允许客户打断")
    enable_emotion_drift: bool = Field(default=True, description="是否启用情绪漂移")
    enable_random_events: bool = Field(default=False, description="是否启用随机事件")
    
    # 评估权重
    goal_weight: float = Field(default=0.4, ge=0.0, le=1.0, description="目标达成权重")
    process_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="过程质量权重")
    compliance_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="合规性权重")
    
    class Config:
        json_schema_extra = {
            "example": {
                "max_turns": 20,
                "timeout_seconds": 600,
                "enable_interruption": True,
                "enable_emotion_drift": True,
                "enable_random_events": False,
                "goal_weight": 0.4,
                "process_weight": 0.3,
                "compliance_weight": 0.3
            }
        }


class SimulationScenario(BaseModel):
    """完整的模拟场景定义"""
    id: str = Field(..., description="场景唯一标识")
    name: str = Field(..., description="场景名称")
    description: str = Field(..., description="场景描述")
    difficulty: DifficultyLevel = Field(..., description="难度等级")
    
    # 核心组件
    customer_profile: CustomerProfile = Field(..., description="客户画像")
    sales_goal: SalesGoal = Field(..., description="销售目标")
    config: ScenarioConfig = Field(default_factory=ScenarioConfig, description="场景配置")
    
    # 上下文信息
    background_context: str = Field(..., description="背景上下文")
    product_info: Dict[str, Any] = Field(default_factory=dict, description="产品信息")
    
    # 元数据
    tags: List[str] = Field(default_factory=list, description="标签")
    author: Optional[str] = Field(None, description="创建者")
    version: str = Field(default="1.0.0", description="版本号")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "scenario_001",
                "name": "SaaS产品冷呼场景",
                "description": "向潜在客户介绍协作工具，争取演示机会",
                "difficulty": "medium",
                "customer_profile": {
                    "name": "李明",
                    "company": "某科技公司",
                    "role": "技术总监",
                    "customer_type": "cold_lead"
                },
                "sales_goal": {
                    "goal_type": "demo",
                    "success_criteria": ["获得演示机会"]
                },
                "background_context": "客户公司正在快速扩张，团队协作工具老旧",
                "tags": ["cold_call", "saas", "b2b"]
            }
        }





