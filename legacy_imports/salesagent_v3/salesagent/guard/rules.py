"""Compliance rule engine — fast regex-based sentence-level checks."""
from __future__ import annotations

import re

from salesagent.core.constants import GuardRiskType

# ── Rule patterns ──────────────────────────────────────────────────────────────

_RULES: list[tuple[GuardRiskType, list[str]]] = [
    (
        GuardRiskType.UNAUTHORIZED_COMMITMENT,
        [
            r"我\s*(?:帮你|可以|能)\s*(?:申请|搞定|搞|拿到)\s*(?:特批|专属|额外)\s*(?:折扣|权限|服务)",
            r"(?:我|我们)\s*保证\s*(?:终身|永久|免费)\s*(?:维护|支持|服务)",
            r"I\s+(?:can|will)\s+(?:guarantee|promise)\s+(?:free|lifetime|unlimited)",
            r"I'll\s+make\s+(?:sure|certain)\s+(?:you\s+get|we\s+provide)\s+unlimited",
        ],
    ),
    (
        GuardRiskType.FALSE_PROMISE,
        [
            r"保证\s*(?:成功|100%|一定|肯定)",
            r"100%\s*(?:保证|确保|承诺|能)",
            r"绝对\s*(?:没问题|可以|保证|做到)",
            r"guarantee[sd]?\s+(?:100|success|results?)",
            r"\b100\s*%\s*(?:guaranteed?|success|work)",
        ],
    ),
    (
        GuardRiskType.PRICE_LEAK,
        [
            r"成本\s*(?:只有|仅|才|不到)\s*[\d¥$]",
            r"内部\s*(?:价格|报价|折扣)\s*是",
            r"私下\s*给你\s*(?:打折|优惠|价)",
            r"actual\s+cost\s+is\s+(?:only|just)\s*[\d$]",
            r"internal\s+pricing",
        ],
    ),
    (
        GuardRiskType.COMPETITOR_DEFAMATION,
        [
            r"(?:比|比起)\s*(?:\w+)\s*(?:差|烂|垃圾|不靠谱|坑人)",
            r"(?:竞品|对手|友商)\s*(?:根本不行|有问题|坑|害|骗)",
            r"(?:far\s+)?(?:worse\s+than|inferior\s+to|much\s+worse)\s+(?:our\s+)?competitors?",
            r"(?:their|competitor's)\s+(?:product|solution)\s+(?:is\s+)?(?:terrible|awful|garbage)",
        ],
    ),
    (
        GuardRiskType.SENSITIVE_INFO,
        [
            r"(?:我们的|我方)\s*(?:真实)?(?:毛利|利润率|成本)\s*(?:是|为|有)",
            r"这个\s*(?:客户|案例|数据)\s*(?:叫|是|名字是)",
            r"(?:confidential|proprietary)\s+(?:cost|margin|profit)",
            r"client\s+(?:name|info|data)\s+is\s+\w+",
        ],
    ),
]

_COMPILED_RULES: list[tuple[GuardRiskType, list[re.Pattern[str]]]] = [
    (risk_type, [re.compile(p, re.IGNORECASE) for p in patterns])
    for risk_type, patterns in _RULES
]


def check_sentence(sentence: str) -> GuardRiskType | None:
    """
    Check a sentence against all compliance rules.
    Returns the first matching GuardRiskType, or None if clean.
    """
    for risk_type, patterns in _COMPILED_RULES:
        for pattern in patterns:
            if pattern.search(sentence):
                return risk_type
    return None


def get_risk_severity(sentence: str) -> tuple[GuardRiskType | None, float]:
    """
    Check sentence and return risk type with severity score.

    Returns:
        (risk_type, severity): severity in [0.0, 1.0]
        - 0.0-0.29: Low risk (可用模板替换)
        - 0.3-0.7: Medium risk (需要 LLM 改写)
        - 0.7-1.0: High risk (必须 LLM 改写 + 人工审核)
    """
    risk_type = check_sentence(sentence)
    if risk_type is None:
        return None, 0.0

    # Calculate severity based on multiple pattern matches
    match_count = 0
    for rt, patterns in _COMPILED_RULES:
        if rt == risk_type:
            for pattern in patterns:
                if pattern.search(sentence):
                    match_count += 1

    # Severity heuristics
    severity = min(0.3 + (match_count - 1) * 0.2, 1.0)

    # Boost severity for critical risk types
    if risk_type in [GuardRiskType.SENSITIVE_INFO, GuardRiskType.UNAUTHORIZED_COMMITMENT]:
        severity = min(severity + 0.2, 1.0)

    return risk_type, severity


import os
import yaml
import json
from typing import Any

def load_sales_values() -> list[dict[str, Any]]:
    """Load sales values from YAML config."""
    path = os.path.join(os.path.dirname(__file__), "sales_values.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data.get("sales_values", [])

SALES_VALUES = load_sales_values()

async def get_semantic_violation(sentence: str, gateway: Any) -> dict[str, Any]:
    """
    Enhanced Guard Node check:
    1. Fast keyword check (fallback)
    2. Semantic Value Alignment check via LLM (optional in Lite Mode)
    """
    from salesagent.core.settings import settings

    # 1. Fast keyword check (regex)
    risk_type = check_sentence(sentence)
    if risk_type:
        return {
            "violation_type": risk_type.value,
            "explanation": "Keyword-based match found.",
            "severity": 0.8
        }

    # 2. Semantic Alignment (Values-based)
    if settings.lite_mode:
        # P0 Cost Optimization: Skip LLM semantic check in Lite Mode
        return {"violation_type": None}

    from salesagent.reasoning.prompts import GUARD_SEMANTIC_CHECK_PROMPT
    try:
        raw = await gateway.complete(
            task="guard_rewrite", # use rewrite model for alignment
            system="You are a sales compliance judge. Be strict about values.",
            user=GUARD_SEMANTIC_CHECK_PROMPT.format(
                sentence=sentence,
                sales_values=yaml.safe_dump(SALES_VALUES, allow_unicode=True)
            ),
            response_format="json"
        )
        res = json.loads(raw)
        return res # {"violation_type": ..., "explanation": ..., "severity": ...}
    except Exception:
        return {"violation_type": None}
