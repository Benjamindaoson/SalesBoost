"""Dual-channel compression for context windows."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.context_manager.prompts import COMPRESSION_PROMPT_TEMPLATE
from app.context_manager.scoring import _score_compliance_risk
from app.infra.llm.interfaces import LLMAdapter
from app.infra.gateway.schemas import ModelConfig

logger = logging.getLogger(__name__)


@dataclass
class StructuredFacts:
    current_stage: Optional[str] = None
    client_profile: Dict[str, str] = None
    objection_state: Dict[str, str] = None
    compliance_log: List[str] = None
    next_best_action: Optional[str] = None
    actionable_delta: Dict[str, Any] = None # Task 4: Actionable Delta (三通道)

    def to_dict(self) -> Dict:
        return {
            "current_stage": self.current_stage,
            "client_profile": self.client_profile or {},
            "objection_state": self.objection_state or {},
            "compliance_log": self.compliance_log or [],
            "next_best_action": self.next_best_action,
            "actionable_delta": self.actionable_delta or {},
        }


@dataclass
class CompressionResult:
    structured_facts: StructuredFacts
    narrative_summary: str
    compliance_hit: bool


async def compress_history(
    history: List[Dict[str, str]],
    current_stage: Optional[str],
    adapter: LLMAdapter,
    model_config: ModelConfig,
    previous_stage: Optional[str] = None,
    previous_facts: Optional[StructuredFacts] = None, # Added for delta calculation
) -> CompressionResult:
    """
    Dual-channel (now 3-channel) compression using LLM.
    Requirement 4: Added Actionable Delta.
    """
    history_text = "\n".join([f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in history])
    
    try:
        prompt = COMPRESSION_PROMPT_TEMPLATE.format(
            current_stage=current_stage or "Unknown",
            previous_stage=previous_stage or "Unknown",
            history_text=history_text
        )

        response_text = await adapter.chat(
            messages=[{"role": "user", "content": prompt}],
            config=model_config
        )

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        data = json.loads(response_text)
        
        sf_data = data.get("structured_facts", {})
        structured = StructuredFacts(
            current_stage=sf_data.get("current_stage"),
            client_profile=sf_data.get("client_profile"),
            objection_state=sf_data.get("objection_state"),
            compliance_log=sf_data.get("compliance_log"),
            next_best_action=sf_data.get("next_best_action"),
        )
        
        # Task 4: Compute Actionable Delta
        structured.actionable_delta = _compute_delta(structured, previous_facts)
        
        return CompressionResult(
            structured_facts=structured,
            narrative_summary=data.get("narrative_summary", ""),
            compliance_hit=data.get("compliance_hit", False)
        )

    except Exception as e:
        logger.error(f"LLM Compression failed: {e}. Falling back to heuristic.")
        return _compress_history_heuristic(history, current_stage, previous_stage, previous_facts)


def _compute_delta(current: StructuredFacts, previous: Optional[StructuredFacts]) -> Dict[str, Any]:
    if not previous:
        return {"new_info": "initial_turn"}
    
    delta = {}
    
    # Check profile changes
    p_profile = previous.client_profile or {}
    c_profile = current.client_profile or {}
    profile_delta = {k: v for k, v in c_profile.items() if v != p_profile.get(k)}
    if profile_delta:
        delta["profile_updates"] = profile_delta
        
    # Check objection changes
    p_obj = previous.objection_state or {}
    c_obj = current.objection_state or {}
    obj_delta = {k: v for k, v in c_obj.items() if v != p_obj.get(k)}
    if obj_delta:
        delta["objection_updates"] = obj_delta
        
    if current.current_stage != previous.current_stage:
        delta["stage_transition"] = f"{previous.current_stage} -> {current.current_stage}"
        
    return delta


def _compress_history_heuristic(
    history: List[Dict[str, str]],
    current_stage: Optional[str],
    previous_stage: Optional[str] = None,
    previous_facts: Optional[StructuredFacts] = None,
) -> CompressionResult:
    text = " ".join([m.get("content", "") for m in history]).strip()
    compliance_hit = _score_compliance_risk(text.lower()) > 0.5
    compliance_log = []
    if compliance_hit:
        compliance_log.append("compliance_risk_detected")

    structured = StructuredFacts(
        current_stage=_normalize_stage(current_stage),
        client_profile=_extract_client_profile(text),
        objection_state=_extract_objection_state(text),
        compliance_log=compliance_log,
        next_best_action=_next_best_action(current_stage, text),
    )
    
    # Task 4: Compute Actionable Delta for heuristic too
    structured.actionable_delta = _compute_delta(structured, previous_facts)

    if compliance_hit:
        narrative = text
    else:
        narrative = _summarize(text, structured, previous_stage, current_stage)

    return CompressionResult(structured_facts=structured, narrative_summary=narrative, compliance_hit=compliance_hit)


def _normalize_stage(stage: Optional[str]) -> Optional[str]:
    if not stage:
        return None
    mapping = {
        "OPENING": "破冰",
        "NEEDS_DISCOVERY": "挖掘",
        "PRODUCT_INTRO": "介绍",
        "OBJECTION_HANDLING": "异议",
        "CLOSING": "成交",
        "COMPLIANCE": "合规",
    }
    return mapping.get(stage, stage)


def _extract_client_profile(text: str) -> Dict[str, str]:
    profile = {}
    if "出差" in text or "飞" in text:
        profile["职业"] = "商旅人士"
    if "里程" in text or "积分" in text:
        profile["偏好"] = "里程兑换"
    if "学生" in text:
        profile["身份"] = "学生"
    if "预算" in text:
        profile["预算敏感"] = "是"
    return profile


def _extract_objection_state(text: str) -> Dict[str, str]:
    if "太贵" in text or "年费" in text or "价格" in text:
        return {"类型": "价格", "状态": "未解决", "策略": "价值锚定法"}
    if "不需要" in text or "用不上" in text:
        return {"类型": "需求", "状态": "未解决", "策略": "需求澄清"}
    if "考虑" in text or "再说" in text:
        return {"类型": "犹豫", "状态": "未解决", "策略": "风险共情"}
    return {}


def _next_best_action(stage: Optional[str], text: str) -> Optional[str]:
    if stage == "NEEDS_DISCOVERY":
        return "继续挖掘场景与预算，确认真实痛点"
    if stage == "PRODUCT_INTRO":
        return "围绕已知痛点做权益匹配，强调价值回报"
    if stage == "OBJECTION_HANDLING":
        if "年费" in text or "价格" in text:
            return "采用价值锚定与回本逻辑化解价格异议"
        return "先确认异议类型，再用对比或证据化解"
    if stage == "CLOSING":
        return "推进确认动作并给出明确下一步"
    return "保持节奏，引导进入需求挖掘"


def _summarize(
    text: str,
    structured: StructuredFacts,
    previous_stage: Optional[str],
    current_stage: Optional[str],
) -> str:
    if not text:
        return ""
    reasons = []
    if structured.objection_state:
        reasons.append("客户出现异议，需要价值重构")
    if structured.client_profile:
        reasons.append("客户画像更新，需匹配权益")
    if not reasons:
        reasons.append("对话推进中，需保持连贯性")
    summary = "；".join(reasons)
    if _stage_jump(previous_stage, current_stage):
        summary = f"{summary}；流程跳跃风险"
    max_len = max(20, int(len(text) * 0.2))
    if len(summary) > max_len:
        summary = summary[: max_len - 1] + "…"
    return summary


def _stage_jump(previous_stage: Optional[str], current_stage: Optional[str]) -> bool:
    order = ["OPENING", "NEEDS_DISCOVERY", "PRODUCT_INTRO", "OBJECTION_HANDLING", "CLOSING"]
    if not previous_stage or not current_stage:
        return False
    try:
        return order.index(current_stage) - order.index(previous_stage) >= 2
    except ValueError:
        return False
