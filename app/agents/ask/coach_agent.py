import logging
import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
import uuid

from app.infra.gateway.model_gateway import ModelGateway
from app.infra.gateway.schemas import ModelCall, RoutingContext, AgentType, LatencyMode
from app.context_manager.state_sync import SalesStateStream
from app.schemas.strategy import (
    StrategyResponse,
    StrategyObject,
    StrategyCategory,
    Evidence,
    EvidenceType,
)
from app.agent_knowledge_interface import get_agent_knowledge_interface

logger = logging.getLogger(__name__)

class Phase(str, Enum):
    OPENING = "opening"
    DISCOVERY = "discovery"
    PROPOSAL = "proposal"
    CLOSING = "closing"

@dataclass
class ComplianceRisk:
    risk_level: str
    sensitive_words: List[str]
    warning_message: str

@dataclass
class CoachAdvice:
    phase: Phase
    detected_phase: Phase
    phase_transition_detected: bool
    customer_intent: str
    action_advice: str
    script_example: str
    compliance_risk: Optional[ComplianceRisk] = None

    def dict(self):
        return {
            "phase": self.phase,
            "detected_phase": self.detected_phase,
            "phase_transition_detected": self.phase_transition_detected,
            "customer_intent": self.customer_intent,
            "action_advice": self.action_advice,
            "script_example": self.script_example,
            "compliance_risk": self.compliance_risk.__dict__ if self.compliance_risk else None
        }

class SalesCoachAgent:
    def __init__(self, model_gateway: ModelGateway = None):
        self.model_gateway = model_gateway or ModelGateway()
        self.state_stream = SalesStateStream()
        self.knowledge = get_agent_knowledge_interface()

    async def propose_strategies(
        self,
        history: List[Dict[str, str]],
        session_id: str,
        blackboard: Optional[Dict[str, Any]] = None,
    ) -> StrategyResponse:
        latest_user = ""
        for msg in reversed(history or []):
            if msg.get("role") in {"sales", "user"}:
                latest_user = msg.get("content", "")
                break

        evidence = [
            Evidence(
                id=f"heuristic:{uuid.uuid4()}",
                source_type=EvidenceType.POLICY_DOC,
                content_snippet="heuristic_strategy_generation",
                metadata={"session_id": session_id},
            )
        ]

        candidates: List[StrategyObject] = []
        lower = (latest_user or "").lower()
        if any(k in lower for k in ["price", "expensive", "cost", "价格", "贵", "多少钱"]):
            candidates.append(
                StrategyObject(
                    strategy_id="value_anchor",
                    category=StrategyCategory.VALUE_PROPOSITION,
                    hypothesis="客户对价格敏感，当前需要用价值锚定降低价格阻力。",
                    expected_effect={"trust": 0.05, "resistance": -0.15, "interest": 0.05},
                    script_candidates=[
                        "我理解你在关注成本，我们先对齐一下你最在意的结果，再看投入是否匹配。",
                        "如果只看价格确实会觉得高，我们更建议看 3 个月能带来的回报与节省的人力时间。",
                    ],
                    evidence=evidence,
                    risks=["avoid_guaranteed_return"],
                )
            )
            candidates.append(
                StrategyObject(
                    strategy_id="probe_constraints",
                    category=StrategyCategory.NEEDS_DISCOVERY,
                    hypothesis="需要进一步确认预算范围与决策约束，避免过早报价。",
                    expected_effect={"trust": 0.1, "resistance": -0.05, "interest": 0.05},
                    script_candidates=[
                        "方便问下你们的预算区间大概是多少？以及这个预算是一次性还是按月度？",
                        "除了价格，你最担心的点是投入产出，还是实施周期和风险？",
                    ],
                    evidence=evidence,
                    risks=[],
                )
            )
        else:
            candidates.append(
                StrategyObject(
                    strategy_id="clarify_need",
                    category=StrategyCategory.NEEDS_DISCOVERY,
                    hypothesis="当前信息不足，需要澄清核心痛点来推进阶段。",
                    expected_effect={"trust": 0.05, "resistance": -0.05, "interest": 0.1},
                    script_candidates=[
                        "我想更准确地帮你判断，能说说你现在最想解决的具体问题是什么吗？",
                        "你希望通过这次方案，优先改善效率、成本还是团队协作？",
                    ],
                    evidence=evidence,
                    risks=[],
                )
            )

        primary_id = candidates[0].strategy_id if candidates else "none"
        return StrategyResponse(
            candidates=candidates,
            primary_recommendation_id=primary_id,
            reasoning="heuristic_strategy_selection",
        )

    async def get_advice(self, history: List[Dict[str, str]], session_id: str, current_context=None, turn_number: int = 0) -> CoachAdvice:
        """
        Generate real-time coaching advice based on conversation history and SalesState.
        """
        logger.info(f"Generating coaching advice for session: {session_id}")
        
        # 1. Fetch SalesState
        latest_state = await self.state_stream.get_latest(session_id)
        sales_stage = "Unknown"
        agent_flags = {}
        
        if latest_state:
             sales_stage = latest_state.get("sales_stage", {}).get("current", "Unknown")
             agent_flags = latest_state.get("agent_flags", {})
             logger.info(f"Coach Agent accessed SalesState: Stage={sales_stage}, Flags={agent_flags}")

        # 2. Check for Immediate Intervention (Compliance/Flags)
        if agent_flags.get("compliance_block"):
             logger.warning("Compliance block detected by Coach. Intervening immediately.")
             return CoachAdvice(
                 phase=Phase(sales_stage) if sales_stage in [p.value for p in Phase] else Phase.DISCOVERY,
                 detected_phase=Phase.DISCOVERY,
                 phase_transition_detected=False,
                 customer_intent="Compliance Risk Detected",
                 action_advice="**STOP**: Compliance violation detected. Do not proceed with this topic.",
                 script_example="I apologize, but I cannot continue with this specific request as it violates our policy.",
                 compliance_risk=ComplianceRisk(risk_level="high", sensitive_words=[], warning_message="Compliance Violation Triggered")
             )
        
        history_text = "\n".join([
            f"{'Sales' if m['role'] == 'sales' else 'Customer'}: {m['content']}"
            for m in history[-5:] # Focus on last 5 turns for context
        ])

        # Get SOP standards for grounding (Context Engineering)
        sop_context = self.knowledge.get_sop_for_coach(
            current_intent=f"{sales_stage}_{latest_user if latest_user else 'general'}",
            top_k=2
        )

        # Build system prompt with SOP grounding
        sop_guidance = ""
        if sop_context['available']:
            sop_guidance = f"""
【标准流程参考 - SOP Grounding】
{sop_context['sop_standard']}

请基于以上标准流程，评估销售人员的表现并提供指导。
"""

        system_prompt = f"""
        You are a Sales Coach. Analyze the conversation and provide actionable advice.
        Current Sales Stage: {sales_stage}

        {sop_guidance}

        Output strictly JSON:
        {{
            "phase": "opening" | "discovery" | "proposal" | "closing",
            "detected_phase": "...",
            "phase_transition_detected": boolean,
            "customer_intent": "...",
            "action_advice": "...",
            "script_example": "...",
            "compliance_risk": null | {{
                "risk_level": "low" | "medium" | "high",
                "sensitive_words": [],
                "warning_message": "..."
            }}
        }}
        """

        call = ModelCall(
            prompt=f"Conversation History:\n{history_text}",
            system_prompt=system_prompt
        )
        
        context = RoutingContext(
            agent_type=AgentType.COACH,
            turn_importance=0.8,
            risk_level="medium",
            budget_remaining=10.0,
            latency_mode=LatencyMode.FAST,
            retrieval_confidence=1.0,
            turn_number=turn_number,
            session_id=session_id,
            budget_authorized=True
        )

        try:
            raw_response = await self.model_gateway.call(call, context)
            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_response:
                raw_response = raw_response.split("```")[1].split("```")[0].strip()
                
            data = json.loads(raw_response)
            
            # Map string phase to Enum
            phase_map = {p.value: p for p in Phase}
            data["phase"] = phase_map.get(data.get("phase"), Phase.DISCOVERY)
            data["detected_phase"] = phase_map.get(data.get("detected_phase"), Phase.DISCOVERY)
            
            if data.get("compliance_risk"):
                data["compliance_risk"] = ComplianceRisk(**data["compliance_risk"])
            
            return CoachAdvice(**data)
            
        except Exception as e:
            logger.error(f"Coaching advice failed: {e}")
            return CoachAdvice(
                phase=Phase.DISCOVERY,
                detected_phase=Phase.DISCOVERY,
                phase_transition_detected=False,
                customer_intent="unknown",
                action_advice="Continue the conversation naturally.",
                script_example="Could you tell me more about that?",
                compliance_risk=None
            )
