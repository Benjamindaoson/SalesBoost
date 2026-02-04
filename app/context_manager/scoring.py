"""Importance scoring for conversation turns."""
from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from app.context_manager.prompts import SCORING_PROMPT_TEMPLATE
from app.infra.llm.interfaces import LLMAdapter
from app.infra.gateway.schemas import ModelConfig

logger = logging.getLogger(__name__)

WEIGHTS = {
    "S": 0.25,
    "D": 0.30,
    "C": 0.20,
    "V": 0.15,
    "N": 0.05,
    "T": 0.05,
}


@dataclass
class ImportanceScores:
    sales_stage_relevance: float
    decision_payload: float
    compliance_risk: float
    champion_reusability: float
    novelty: float
    timeliness: float
    final_score: float
    persistent: bool
    reasoning: Optional[str] = None


async def compute_importance_score(
    user_input: str,
    npc_response: str,
    current_stage: Optional[str],
    adapter: LLMAdapter,
    model_config: ModelConfig,
    known_facts: Optional[Iterable[str]] = None,
) -> ImportanceScores:
    """
    Compute importance score using LLM evaluation based on the System Prompt.
    Falls back to heuristic if LLM fails.
    """
    try:
        prompt = SCORING_PROMPT_TEMPLATE.format(
            current_stage=current_stage or "Unknown",
            user_input=user_input,
            npc_response=npc_response,
            known_facts=", ".join(known_facts or [])
        )

        response_text = await adapter.chat(
            messages=[{"role": "user", "content": prompt}],
            config=model_config
        )
        
        # Clean markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        data = json.loads(response_text)
        
        return ImportanceScores(
            sales_stage_relevance=float(data.get("sales_stage_relevance", 0.0)),
            decision_payload=float(data.get("decision_payload", 0.0)),
            compliance_risk=float(data.get("compliance_risk", 0.0)),
            champion_reusability=float(data.get("champion_reusability", 0.0)),
            novelty=float(data.get("novelty", 0.0)),
            timeliness=float(data.get("timeliness", 0.0)),
            final_score=float(data.get("final_score", 0.0)),
            persistent=bool(data.get("persistent", False)),
            reasoning=data.get("reasoning", "")
        )

    except Exception as e:
        logger.error(f"LLM Scoring failed: {e}. Falling back to heuristic.")
        return _compute_importance_score_heuristic(
            user_input, npc_response, current_stage, known_facts
        )


def _compute_importance_score_heuristic(
    user_input: str,
    npc_response: str,
    current_stage: Optional[str],
    known_facts: Optional[Iterable[str]] = None,
) -> ImportanceScores:
    text = f"{user_input} {npc_response}".strip()
    lower = text.lower()

    s = _score_sales_stage_relevance(lower, current_stage)
    d = _score_decision_payload(lower)
    c = _score_compliance_risk(lower)
    v = _score_champion_reusability(npc_response or "")
    n = _score_novelty(lower, known_facts or [])
    t = 1.0

    if c > 0.5:
        final = 1.0
    else:
        final = (
            WEIGHTS["S"] * s
            + WEIGHTS["D"] * d
            + WEIGHTS["C"] * c
            + WEIGHTS["V"] * v
            + WEIGHTS["N"] * n
            + WEIGHTS["T"] * t
        )
    persistent = final >= 0.75
    return ImportanceScores(
        sales_stage_relevance=round(s, 3),
        decision_payload=round(d, 3),
        compliance_risk=round(c, 3),
        champion_reusability=round(v, 3),
        novelty=round(n, 3),
        timeliness=round(t, 3),
        final_score=round(final, 3),
        persistent=persistent,
        reasoning="Heuristic fallback"
    )


def _score_sales_stage_relevance(text: str, current_stage: Optional[str]) -> float:
    stage_keywords = {
        "OPENING": ["你好", "您好", "初次", "很高兴", "认识你"],
        "NEEDS_DISCOVERY": ["需求", "痛点", "场景", "预算", "使用频率", "目标"],
        "PRODUCT_INTRO": ["权益", "功能", "方案", "产品", "价值", "优势", "配置"],
        "OBJECTION_HANDLING": ["太贵", "不需要", "考虑", "担心", "不合适", "异议"],
        "CLOSING": ["办理", "下单", "签约", "推进", "确认", "成交"],
        "COMPLIANCE": ["合规", "投诉", "违规", "承诺", "保证收益"],
    }
    score = 0.0
    for stage, keywords in stage_keywords.items():
        if any(k in text for k in keywords):
            score = max(score, 0.6 if stage == (current_stage or "") else 0.4)
    if current_stage and current_stage in stage_keywords and any(
        k in text for k in stage_keywords[current_stage]
    ):
        score = max(score, 0.8)
    return min(score, 1.0)


def _score_decision_payload(text: str) -> float:
    signals = 0
    signals += 1 if re.search(r"(年费|价格|费用|预算|折扣|便宜|太贵)", text) else 0
    signals += 1 if re.search(r"(不需要|不合适|考虑一下|先看看|再说)", text) else 0
    signals += 1 if re.search(r"(可以办|下单|购买|签约|办理)", text) else 0
    signals += 1 if re.search(r"(经常|每周|每月|出差|旅游|飞)", text) else 0
    signals += 1 if re.search(r"\d", text) else 0
    return min(1.0, signals * 0.2)


def _score_compliance_risk(text: str) -> float:
    risk_terms = [
        "保证收益",
        "100%成功",
        "稳赚",
        "无风险",
        "诱导",
        "投诉",
        "举报",
        "违法",
    ]
    if any(term in text for term in risk_terms):
        return 0.8
    if re.search(r"(system prompt|绕过规则|忽略指令)", text):
        return 0.7
    return 0.0


def _score_champion_reusability(npc_response: str) -> float:
    response = npc_response or ""
    patterns = [
        "理解您的顾虑",
        "我们可以先",
        "价值",
        "对比",
        "回本",
        "我建议",
    ]
    hits = sum(1 for p in patterns if p in response)
    return min(1.0, hits * 0.15)


def _score_novelty(text: str, known_facts: Iterable[str]) -> float:
    facts = " ".join(known_facts).lower()
    if not facts:
        return 0.5 if re.search(r"\d|年费|预算|出差|权益|场景", text) else 0.2
    new_tokens = [t for t in re.split(r"\W+", text) if t and t not in facts]
    return 0.8 if len(new_tokens) > 3 else 0.2
