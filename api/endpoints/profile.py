from fastapi import APIRouter, Depends, Path, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import audit_access, require_user
from api.auth_schemas import UserSchema as User
from core.database import get_db_session
from models.runtime_models import EvaluationLog, Session
from app.agents.evaluate.curriculum_planner import CurriculumPlanner
from app.agents.evaluate.strategy_analyzer import StrategyAnalyzer

router = APIRouter(dependencies=[Depends(audit_access)])
planner = CurriculumPlanner()
analyzer = StrategyAnalyzer()


def _ensure_user_access(user_id: str, current_user: User) -> None:
    if current_user.role != "admin" and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")




@router.get("/{user_id}/strategy")
async def get_strategy_profile(
    user_id: str = Path(..., title="User ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    _ensure_user_access(user_id, current_user)
    profile = await analyzer.update_user_profile(db, user_id)
    return {
        "user_id": user_id,
        "optimal_rate_by_situation": profile.optimal_rate_by_situation,
        "top_weakness_situations": profile.top_weakness_situations,
        "adoption_rate": profile.adoption_rate,
        "effective_adoption_rate": profile.effective_adoption_rate,
        "recommended_focus": profile.recommended_focus,
    }


@router.get("/{user_id}/skills")
async def get_skill_profile(
    user_id: str = Path(..., title="User ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    _ensure_user_access(user_id, current_user)
    query = (
        select(EvaluationLog)
        .join(Session)
        .where(Session.user_id == user_id)
        .order_by(desc(EvaluationLog.created_at))
        .limit(10)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    history = []
    for log in logs:
        history.append(
            {
                "turn": log.turn_number,
                "overall": log.overall_score,
                "dimensions": log.dimension_scores,
                "timestamp": log.created_at,
            }
        )

    return {"user_id": user_id, "history": history}


@router.get("/{user_id}/skill-trajectory")
async def get_skill_trajectory(
    user_id: str = Path(..., title="User ID"),
    days: int = 30,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    _ensure_user_access(user_id, current_user)
    limit = days * 5

    query = (
        select(EvaluationLog)
        .join(Session)
        .where(Session.user_id == user_id)
        .order_by(EvaluationLog.created_at.asc())
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    trajectory = {
        "dates": [],
        "overall": [],
        "integrity": [],
        "relevance": [],
        "correctness": [],
        "logic": [],
        "compliance": [],
    }

    for log in logs:
        trajectory["dates"].append(log.created_at.isoformat() if log.created_at else "N/A")
        trajectory["overall"].append(log.overall_score)
        trajectory["integrity"].append(log.dimension_scores.get("integrity", {}).get("score", 0))
        trajectory["relevance"].append(log.dimension_scores.get("relevance", {}).get("score", 0))
        trajectory["correctness"].append(log.dimension_scores.get("correctness", {}).get("score", 0))
        trajectory["logic"].append(log.dimension_scores.get("logic", {}).get("score", 0))
        trajectory["compliance"].append(log.dimension_scores.get("compliance", {}).get("score", 0))

    return {
        "user_id": user_id,
        "period_days": days,
        "data_points": len(logs),
        "trajectory": trajectory,
    }


@router.get("/{user_id}/strategy-gap")
async def get_strategy_gap(
    user_id: str = Path(..., title="User ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    _ensure_user_access(user_id, current_user)
    deviation_stats = await analyzer.get_strategy_deviation_stats(db, user_id, limit=20)

    benchmark_optimal_rate = 0.85
    gap_analysis = []

    for stat in deviation_stats:
        user_rate = stat["optimal_rate"]
        gap = benchmark_optimal_rate - user_rate

        status = "Good"
        if gap > 0.3:
            status = "Critical Gap"
        elif gap > 0.1:
            status = "Moderate Gap"

        gap_analysis.append(
            {
                "situation": stat["situation_type"],
                "user_success_rate": round(user_rate * 100, 1),
                "top_performer_rate": round(benchmark_optimal_rate * 100, 1),
                "gap_percentage": round(gap * 100, 1),
                "status": status,
                "golden_strategy": stat["golden_strategy"],
            }
        )

    gap_analysis.sort(key=lambda x: x["gap_percentage"], reverse=True)

    return {
        "user_id": user_id,
        "benchmark_source": "Top 10% Performers (Static Baseline)",
        "gaps": gap_analysis,
    }


@router.get("/{user_id}/why-not-improved")
async def explain_lack_of_improvement(
    user_id: str = Path(..., title="User ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    _ensure_user_access(user_id, current_user)
    adoption_stats = await planner._get_adoption_stats(db, user_id)
    deviation_stats = await analyzer.get_strategy_deviation_stats(db, user_id, limit=5)

    reasons = []
    evidence = []

    adoption_rate = adoption_stats.get("adoption_rate", 0)
    if adoption_rate < 0.3:
        reasons.append("Low adoption rate")
        evidence.append(f"Adoption Rate: {adoption_rate*100:.1f}% (Benchmark: >50%)")

    effective_rate = adoption_stats.get("effective_adoption_rate", 0)
    if effective_rate < 0.4 and adoption_rate >= 0.3:
        reasons.append("Ineffective execution")
        evidence.append(f"Effectiveness Rate: {effective_rate*100:.1f}% (Benchmark: >60%)")

    deviations = [d for d in deviation_stats if d.get("is_deviation")]
    if deviations:
        top_dev = deviations[0]
        reasons.append(
            f"Strategy mismatch in '{top_dev['situation_type']}'"
        )
        evidence.append(
            f"Situation: {top_dev['situation_type']}. You chose: '{top_dev['strategy_chosen']}'. "
            f"Top performers use: '{top_dev['golden_strategy']}'."
        )

    if not reasons:
        reasons.append("No obvious blockers found yet")

    return {
        "user_id": user_id,
        "diagnosis": reasons,
        "evidence": evidence,
        "actionable_feedback": "Focus on using the recommended strategy in the next turn.",
        "stats_summary": {
            "adoption_rate": adoption_rate,
            "effectiveness_rate": effective_rate,
            "top_deviation": deviations[0]["situation_type"] if deviations else None,
        },
    }


@router.get("/{user_id}/why-this-curriculum")
async def explain_curriculum_choice(
    user_id: str = Path(..., title="User ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
):
    _ensure_user_access(user_id, current_user)
    plan = await planner.generate_curriculum(db, user_id, max_focus_items=1)

    if not plan.next_training_plan:
        return {
            "user_id": user_id,
            "reasoning": "No specific weakness detected. Maintenance mode.",
            "focus": "General Practice",
        }

    focus = plan.next_training_plan[0]

    explanation = {
        "user_id": user_id,
        "recommended_focus": {
            "situation": focus.focus_situation,
            "strategy": focus.focus_strategy,
            "stage": focus.stage,
        },
        "why_this_situation": (
            f"Your optimal decision rate in '{focus.focus_situation}' is below benchmark."
        ),
        "why_this_strategy": (
            f"Top performers achieve 85%+ success with '{focus.focus_strategy}' here."
        ),
        "expected_outcome": plan.expected_improvement,
        "raw_reasoning": plan.reasoning,
    }

    return explanation
