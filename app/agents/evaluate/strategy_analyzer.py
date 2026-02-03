import logging
import json
from dataclasses import dataclass
from typing import List, Dict, Any

from app.infra.gateway.model_gateway import ModelGateway
from app.infra.gateway.schemas import ModelCall, RoutingContext
from app.agent_knowledge_interface import get_agent_knowledge_interface

logger = logging.getLogger(__name__)

@dataclass
class StrategyProfile:
    optimal_rate_by_situation: dict
    top_weakness_situations: list
    adoption_rate: float
    effective_adoption_rate: float
    recommended_focus: str

class StrategyAnalyzer:
    def __init__(self, model_gateway: ModelGateway = None):
        self.model_gateway = model_gateway or ModelGateway()
        self.knowledge = get_agent_knowledge_interface()

    async def analyze_strategy_deviation(self, session_id: str, messages: List[Any]) -> Dict[str, Any]:
        """
        Analyze how the user's strategy deviates from the 'Sales Champion' strategy.
        Uses In-Context Learning with champion cases for Few-Shot analysis.
        """
        logger.info(f"Analyzing strategy for session: {session_id}")

        history_text = "\n".join([
            f"{'Sales' if m.role == 'sales' else 'Customer'}: {m.content}"
            for m in messages
        ])

        # Get last user message for champion case retrieval
        last_user_msg = ""
        for m in reversed(messages):
            if m.role in {"sales", "user"}:
                last_user_msg = m.content
                break

        # Get champion cases for In-Context Learning (Few-Shot)
        champion_context = self.knowledge.get_context_for_analyst(
            user_dialogue=last_user_msg or history_text[:200],
            top_k=2
        )

        # Build Few-Shot prompt with champion cases
        champion_examples = ""
        if champion_context['available']:
            champion_examples = f"""
【参考案例 - 销售冠军的实战经验】
{champion_context['champion_case']}

请基于以上冠军的实战经验，分析用户的销售策略与冠军做法的差距。
"""

        system_prompt = f"""
        You are a Sales Strategy Analyst.
        Compare the user's sales performance against 'Best Practices' (Sales Champion).
        Identify key situations where the user could have used a better strategy.

        {champion_examples}

        Output JSON:
        {{
            "strategy_comparisons": [
                {{
                    "situation_type": "objection_handling",
                    "situation_name_cn": "处理价格异议",
                    "your_strategy": "Direct discount",
                    "champion_strategy": "Value reinforcement before discount",
                    "is_optimal": false,
                    "occurrence_count": 1,
                    "optimal_rate": 0.0
                }}
            ],
            "overall_optimal_rate": float (0-1),
            "recommended_focus": "..."
        }}
        """

        call = ModelCall(
            prompt=f"Conversation History:\n{history_text}",
            system_prompt=system_prompt
        )
        context = RoutingContext(session_id=session_id, agent_type="strategy_analyzer")

        try:
            raw_response = await self.model_gateway.call(call, context)
            analysis = json.loads(raw_response.strip("```json").strip("```"))
            return analysis
        except Exception as e:
            logger.error(f"Strategy analysis failed: {e}")
            return {
                "strategy_comparisons": [],
                "overall_optimal_rate": 0.0,
                "recommended_focus": "Analysis unavailable"
            }

    async def update_user_profile(self, db, user_id: str) -> StrategyProfile:
        """
        Update the long-term strategy profile for a user based on historical data.
        (Simplified version for now)
        """
        return StrategyProfile(
            optimal_rate_by_situation={},
            top_weakness_situations=[],
            adoption_rate=0.7,
            effective_adoption_rate=0.5,
            recommended_focus="Focus on closing techniques"
        )
