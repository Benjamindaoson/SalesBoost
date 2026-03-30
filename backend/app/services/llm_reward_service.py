"""
LLM-as-Judge Reward Service

方案 A: 用 LLM 评分替代手写 Reward，提供更准确的反馈信号。
替代 agents/rl/reward_model.py 中的规则式奖励。
"""
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..infra.gateway.model_gateway import ModelGateway
from ..infra.gateway.schemas import ModelCall, RoutingContext, AgentType, LatencyMode

logger = logging.getLogger(__name__)

REWARD_PROMPT = """你是一个销售对话质量评估专家。根据以下信息，给出 0-10 的总体评分，以及各维度分数。

对话片段（最近几轮）：
{history}

销售人员本轮表现：{sales_response}
客户反应：{customer_response}

评估维度（各 0-10）：
- task_progress: 是否推进了销售阶段
- quality: 表达清晰、专业
- satisfaction: 客户满意度信号
- efficiency: 是否简洁高效
- compliance: 是否合规

仅返回 JSON：
{{"overall": 7.5, "task_progress": 7, "quality": 8, "satisfaction": 7, "efficiency": 8, "compliance": 10, "reasoning": "简短理由"}}
"""


@dataclass
class LLMRewardResult:
    """LLM 评分结果"""
    overall: float
    task_progress: float
    quality: float
    satisfaction: float
    efficiency: float
    compliance: float
    reasoning: str
    raw_components: Dict[str, float]


class LLMRewardService:
    """LLM-as-Judge 奖励服务"""

    def __init__(self, gateway: Optional[ModelGateway] = None):
        self.gateway = gateway or ModelGateway()

    async def score_turn(
        self,
        history: List[Dict[str, str]],
        sales_response: str,
        customer_response: str,
        session_id: str = "reward",
    ) -> LLMRewardResult:
        """对单轮对话进行 LLM 评分"""
        history_text = "\n".join(
            f"{m.get('role','user')}: {m.get('content','')}" for m in history[-6:]
        )
        prompt = REWARD_PROMPT.format(
            history=history_text[:800],
            sales_response=(sales_response or "")[:400],
            customer_response=(customer_response or "")[:400],
        )
        call = ModelCall(prompt=prompt, system_prompt="你只输出 JSON。")
        ctx = RoutingContext(
            session_id=session_id,
            agent_type=AgentType.COACH,
            turn_importance=0.5,
            risk_level="low",
            budget_remaining=10.0,
            latency_mode=LatencyMode.FAST,
            retrieval_confidence=1.0,
            turn_number=0,
            budget_authorized=True,
        )
        try:
            raw = await self.gateway.call(call, ctx)
            raw = raw.strip()
            if "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            data = json.loads(raw)
            return LLMRewardResult(
                overall=float(data.get("overall", 7.0)),
                task_progress=float(data.get("task_progress", 7.0)),
                quality=float(data.get("quality", 7.0)),
                satisfaction=float(data.get("satisfaction", 7.0)),
                efficiency=float(data.get("efficiency", 7.0)),
                compliance=float(data.get("compliance", 10.0)),
                reasoning=str(data.get("reasoning", "")),
                raw_components={k: v for k, v in data.items() if isinstance(v, (int, float))},
            )
        except Exception as e:
            logger.warning("LLM reward failed: %s, returning default", e)
            return LLMRewardResult(
                overall=7.0,
                task_progress=7.0,
                quality=7.0,
                satisfaction=7.0,
                efficiency=7.0,
                compliance=10.0,
                reasoning="LLM scoring unavailable",
                raw_components={},
            )


llm_reward_service = LLMRewardService()
