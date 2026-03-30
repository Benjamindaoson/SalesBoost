"""
Sales Methodology Engine

Supports MEDDPICC, SPIN, and Challenger frameworks.
Provides dimension tracking, scoring, gap analysis, and coaching recommendations.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MethodologyFramework(str, PyEnum):
    MEDDPICC = "meddpicc"
    SPIN = "spin"
    CHALLENGER = "challenger"


class DimensionStatus(str, PyEnum):
    UNKNOWN = "unknown"
    PARTIAL = "partial"
    CONFIRMED = "confirmed"


# ---------------------------------------------------------------------------
# Framework Definitions
# ---------------------------------------------------------------------------

FRAMEWORK_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "meddpicc": {
        "label": "MEDDPICC",
        "dimensions": {
            "metrics": {
                "label": "Metrics (量化指标)",
                "description": "客户期望的量化回报是什么？",
                "weight": 1.0,
                "probe_questions": [
                    "客户的关键业务指标有哪些？",
                    "他们期望的ROI或回报周期是多少？",
                    "成功的量化标准是什么？",
                ],
            },
            "economic_buyer": {
                "label": "Economic Buyer (决策人)",
                "description": "谁有预算决策权？",
                "weight": 1.5,
                "probe_questions": [
                    "谁是最终的预算审批人？",
                    "决策人对这个项目的态度如何？",
                    "你是否直接接触过决策人？",
                ],
            },
            "decision_criteria": {
                "label": "Decision Criteria (决策标准)",
                "description": "客户用什么标准评估？",
                "weight": 1.0,
                "probe_questions": [
                    "客户的评估标准是什么？",
                    "技术要求、商务条件各占多大比重？",
                    "我们在哪些标准上有优势？",
                ],
            },
            "decision_process": {
                "label": "Decision Process (决策流程)",
                "description": "决策流程是什么？几个环节？",
                "weight": 1.0,
                "probe_questions": [
                    "从评估到签约需要几个步骤？",
                    "有哪些人参与决策？",
                    "预计的决策时间线是？",
                ],
            },
            "paper_process": {
                "label": "Paper Process (采购流程)",
                "description": "合同/法务/采购流程是？",
                "weight": 0.8,
                "probe_questions": [
                    "采购审批需要几级？",
                    "法务审核一般需要多久？",
                    "是否需要招投标？",
                ],
            },
            "identify_pain": {
                "label": "Identify Pain (痛点)",
                "description": "核心业务痛点是什么？",
                "weight": 1.2,
                "probe_questions": [
                    "客户当前面临的最大挑战是什么？",
                    "这个痛点造成了多大损失？",
                    "不解决会有什么后果？",
                ],
            },
            "champion": {
                "label": "Champion (内部倡导者)",
                "description": "谁在内部帮我们推？",
                "weight": 1.3,
                "probe_questions": [
                    "谁是我们在客户内部的支持者？",
                    "他们有足够的影响力吗？",
                    "他们为什么愿意帮我们？",
                ],
            },
            "competition": {
                "label": "Competition (竞争)",
                "description": "竞品是谁？客户在对比什么？",
                "weight": 0.8,
                "probe_questions": [
                    "客户还在评估哪些竞品？",
                    "竞品的优劣势是什么？",
                    "客户是否考虑维持现状不采购？",
                ],
            },
        },
    },
    "spin": {
        "label": "SPIN",
        "dimensions": {
            "situation": {
                "label": "Situation (情境问题)",
                "description": "了解客户现状",
                "weight": 0.8,
                "probe_questions": [
                    "客户目前用什么方案？",
                    "团队规模和业务流程是怎样的？",
                    "当前的工具和系统有哪些？",
                ],
            },
            "problem": {
                "label": "Problem (难点问题)",
                "description": "挖掘显性痛点",
                "weight": 1.0,
                "probe_questions": [
                    "当前方案有什么不满意的地方？",
                    "哪些环节效率最低？",
                    "遇到过什么具体困难？",
                ],
            },
            "implication": {
                "label": "Implication (影响问题)",
                "description": "放大痛点后果",
                "weight": 1.3,
                "probe_questions": [
                    "这个问题如果不解决，会带来什么影响？",
                    "对业务增长的影响有多大？",
                    "对团队士气有什么影响？",
                ],
            },
            "need_payoff": {
                "label": "Need-Payoff (价值问题)",
                "description": "引导客户说出需求",
                "weight": 1.5,
                "probe_questions": [
                    "如果解决了这个问题，会带来什么好处？",
                    "理想的解决方案是什么样的？",
                    "这对你们的业务意味着什么？",
                ],
            },
        },
    },
    "challenger": {
        "label": "Challenger",
        "dimensions": {
            "teach": {
                "label": "Teach (教育)",
                "description": "提供客户不知道的洞察",
                "weight": 1.2,
                "probe_questions": [
                    "是否向客户分享了行业洞察？",
                    "客户是否认识到了之前忽略的问题？",
                    "是否重新定义了客户对问题的理解？",
                ],
            },
            "tailor": {
                "label": "Tailor (定制)",
                "description": "针对客户角色定制信息",
                "weight": 1.0,
                "probe_questions": [
                    "是否针对不同角色准备了不同的价值主张？",
                    "信息是否与客户的具体业务场景关联？",
                    "是否使用了客户行业的语言和案例？",
                ],
            },
            "take_control": {
                "label": "Take Control (掌控)",
                "description": "主导对话节奏和方向",
                "weight": 1.3,
                "probe_questions": [
                    "是否清晰地提出了下一步建议？",
                    "在价格讨论中是否保持了主动？",
                    "是否在合适的时机推进了成交？",
                ],
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

class DimensionState:
    """State of a single methodology dimension."""

    def __init__(
        self,
        status: str = DimensionStatus.UNKNOWN,
        evidence: str = "",
        updated_at: Optional[str] = None,
    ):
        self.status = status
        self.evidence = evidence
        self.updated_at = updated_at or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "evidence": self.evidence,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DimensionState":
        return cls(
            status=data.get("status", DimensionStatus.UNKNOWN),
            evidence=data.get("evidence", ""),
            updated_at=data.get("updated_at"),
        )


class MethodologyState:
    """Full methodology state for a Deal."""

    def __init__(
        self,
        framework: str = MethodologyFramework.MEDDPICC,
        dimensions: Optional[Dict[str, DimensionState]] = None,
    ):
        self.framework = framework
        defn = FRAMEWORK_DEFINITIONS.get(framework, {})
        dim_keys = defn.get("dimensions", {}).keys()

        if dimensions:
            self.dimensions = dimensions
        else:
            self.dimensions = {k: DimensionState() for k in dim_keys}

    @property
    def overall_score(self) -> float:
        """Weighted completion score 0-100."""
        defn = FRAMEWORK_DEFINITIONS.get(self.framework, {})
        dim_defs = defn.get("dimensions", {})
        total_weight = 0.0
        earned = 0.0
        for key, dim_state in self.dimensions.items():
            w = dim_defs.get(key, {}).get("weight", 1.0)
            total_weight += w
            if dim_state.status == DimensionStatus.CONFIRMED:
                earned += w
            elif dim_state.status == DimensionStatus.PARTIAL:
                earned += w * 0.5
        return round((earned / total_weight) * 100, 1) if total_weight else 0.0

    @property
    def next_focus(self) -> Optional[str]:
        """AI recommendation: which dimension to focus on next (highest-weight unknown)."""
        defn = FRAMEWORK_DEFINITIONS.get(self.framework, {})
        dim_defs = defn.get("dimensions", {})
        candidates = []
        for key, dim_state in self.dimensions.items():
            if dim_state.status != DimensionStatus.CONFIRMED:
                w = dim_defs.get(key, {}).get("weight", 1.0)
                candidates.append((key, w))
        candidates.sort(key=lambda x: -x[1])
        return candidates[0][0] if candidates else None

    def gap_analysis(self) -> List[Dict[str, Any]]:
        """Return gaps sorted by priority (weight desc)."""
        defn = FRAMEWORK_DEFINITIONS.get(self.framework, {})
        dim_defs = defn.get("dimensions", {})
        gaps = []
        for key, dim_state in self.dimensions.items():
            if dim_state.status != DimensionStatus.CONFIRMED:
                dd = dim_defs.get(key, {})
                gaps.append({
                    "dimension": key,
                    "label": dd.get("label", key),
                    "status": dim_state.status,
                    "weight": dd.get("weight", 1.0),
                    "description": dd.get("description", ""),
                    "probe_questions": dd.get("probe_questions", []),
                })
        gaps.sort(key=lambda g: -g["weight"])
        return gaps

    def update_dimension(self, dimension: str, status: str, evidence: str = "") -> None:
        if dimension in self.dimensions:
            self.dimensions[dimension].status = status
            if evidence:
                existing = self.dimensions[dimension].evidence
                self.dimensions[dimension].evidence = (
                    f"{existing}; {evidence}" if existing else evidence
                )
            self.dimensions[dimension].updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "framework": self.framework,
            "dimensions": {k: v.to_dict() for k, v in self.dimensions.items()},
            "overall_score": self.overall_score,
            "next_focus": self.next_focus,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MethodologyState":
        framework = data.get("framework", MethodologyFramework.MEDDPICC)
        dims_raw = data.get("dimensions", {})
        dims = {k: DimensionState.from_dict(v) for k, v in dims_raw.items()}
        return cls(framework=framework, dimensions=dims)

    @classmethod
    def from_json(cls, json_str: str) -> "MethodologyState":
        if not json_str:
            return cls()
        return cls.from_dict(json.loads(json_str))


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class MethodologyEngine:
    """
    Core engine that powers methodology-driven coaching.

    Responsibilities:
    - Create initial state for a deal
    - Analyze conversation to detect methodology dimension progress
    - Score deals
    - Generate coaching prompts based on gaps
    - Compute aggregate stats for the cockpit
    """

    @staticmethod
    def create_state(framework: str = MethodologyFramework.MEDDPICC) -> MethodologyState:
        return MethodologyState(framework=framework)

    @staticmethod
    def get_framework_definition(framework: str) -> Dict[str, Any]:
        return FRAMEWORK_DEFINITIONS.get(framework, {})

    @staticmethod
    def list_frameworks() -> List[Dict[str, str]]:
        return [
            {"id": k, "label": v["label"]}
            for k, v in FRAMEWORK_DEFINITIONS.items()
        ]

    @staticmethod
    def score(state: MethodologyState) -> float:
        return state.overall_score

    @staticmethod
    def generate_prep_prompt(state: MethodologyState, customer_info: str = "") -> str:
        """Generate a battle-prep prompt that highlights gaps and suggests focus areas."""
        gaps = state.gap_analysis()
        if not gaps:
            return "所有方法论维度已确认。建议聚焦成交推进。"

        defn = FRAMEWORK_DEFINITIONS.get(state.framework, {})
        framework_label = defn.get("label", state.framework)

        lines = [f"## {framework_label} 战前检查\n"]
        lines.append(f"当前完成度：{state.overall_score}%\n")

        if customer_info:
            lines.append(f"客户信息：{customer_info}\n")

        lines.append("### 待补全维度（按优先级排序）\n")
        for g in gaps[:3]:
            lines.append(f"**{g['label']}** — {g['description']}")
            lines.append(f"  状态：{g['status']}")
            if g["probe_questions"]:
                lines.append("  建议提问：")
                for q in g["probe_questions"]:
                    lines.append(f"    - {q}")
            lines.append("")

        lines.append("### 本次沟通建议")
        top = gaps[0]
        lines.append(f"重点突破 **{top['label']}**：{top['description']}")

        return "\n".join(lines)

    @staticmethod
    def generate_live_coaching_context(state: MethodologyState) -> Dict[str, Any]:
        """Context injected into the Coach Agent during live assist."""
        gaps = state.gap_analysis()
        return {
            "framework": state.framework,
            "score": state.overall_score,
            "next_focus": state.next_focus,
            "gaps": [
                {
                    "dimension": g["dimension"],
                    "label": g["label"],
                    "probe_questions": g["probe_questions"][:2],
                }
                for g in gaps[:3]
            ],
            "confirmed": [
                k for k, v in state.dimensions.items()
                if v.status == DimensionStatus.CONFIRMED
            ],
        }

    @staticmethod
    def generate_review_report(
        state_before: MethodologyState,
        state_after: MethodologyState,
    ) -> Dict[str, Any]:
        """Generate a structured review comparing before/after methodology state."""
        dimensions_delta = {}
        for key in state_after.dimensions:
            before_status = state_before.dimensions.get(key, DimensionState()).status
            after = state_after.dimensions[key]
            changed = before_status != after.status
            dimensions_delta[key] = {
                "before": before_status,
                "after": after.status,
                "evidence": after.evidence,
                "changed": changed,
            }

        advanced = [k for k, v in dimensions_delta.items() if v["changed"] and v["after"] in (DimensionStatus.PARTIAL, DimensionStatus.CONFIRMED)]
        still_missing = [k for k, v in dimensions_delta.items() if v["after"] == DimensionStatus.UNKNOWN]

        return {
            "framework": state_after.framework,
            "score_before": state_before.overall_score,
            "score_after": state_after.overall_score,
            "score_delta": round(state_after.overall_score - state_before.overall_score, 1),
            "dimensions_delta": dimensions_delta,
            "advanced_dimensions": advanced,
            "still_missing": still_missing,
            "next_focus": state_after.next_focus,
        }

    @staticmethod
    def suggest_stage_from_score(score: float) -> str:
        """Map methodology score to suggested pipeline stage."""
        if score < 15:
            return "lead"
        elif score < 35:
            return "qualified"
        elif score < 60:
            return "proposal"
        elif score < 80:
            return "negotiation"
        else:
            return "closed_won"

    @staticmethod
    def aggregate_team_stats(deals_states: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate methodology stats across multiple deals for cockpit."""
        if not deals_states:
            return {"avg_score": 0, "dimension_averages": {}, "weakest": None, "total_deals": 0}

        all_dims: Dict[str, List[float]] = {}
        scores = []

        for ds in deals_states:
            state = MethodologyState.from_dict(ds)
            scores.append(state.overall_score)
            defn = FRAMEWORK_DEFINITIONS.get(state.framework, {})
            dim_defs = defn.get("dimensions", {})

            for key, dim_state in state.dimensions.items():
                if key not in all_dims:
                    all_dims[key] = []
                val = 0.0
                if dim_state.status == DimensionStatus.CONFIRMED:
                    val = 100.0
                elif dim_state.status == DimensionStatus.PARTIAL:
                    val = 50.0
                all_dims[key].append(val)

        dim_avgs = {k: round(sum(v) / len(v), 1) for k, v in all_dims.items()}
        weakest = min(dim_avgs, key=dim_avgs.get) if dim_avgs else None

        return {
            "avg_score": round(sum(scores) / len(scores), 1),
            "dimension_averages": dim_avgs,
            "weakest": weakest,
            "total_deals": len(deals_states),
        }
