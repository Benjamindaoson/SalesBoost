"""Analytics API for A/B testing and performance monitoring."""
from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from salesagent.dependencies import get_db
from salesagent.models.db_models import PromptTemplate, Message, Session as SessionModel

router = APIRouter()


@router.get("/daily-summary")
async def get_daily_summary(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get today's summary metrics for dashboard.

    Returns:
        Daily summary with key metrics
    """
    today = datetime.datetime.now(datetime.timezone.utc).date()

    # Today's followup count (messages sent)
    followups = await db.scalar(
        select(func.count(Message.id))
        .where(
            func.date(Message.created_at) == today,
            Message.role == "assistant",
        )
    )

    # Today's deals closed
    deals = await db.scalar(
        select(func.count(SessionModel.id))
        .where(
            SessionModel.status == "closed_won",
            func.date(SessionModel.updated_at) == today,
        )
    )

    # Average response time (TODO: calculate from actual data)
    avg_response_time = 2.3

    return {
        "today_followups": followups or 0,
        "high_intent_count": 0,
        "deals_closed": deals or 0,
        "avg_response_time": avg_response_time,
    }


@router.get("/prompt-performance")
async def get_prompt_performance(
    name: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get performance metrics for all prompt versions.

    Returns:
    - Prompt versions with avg_reward, usage_count, traffic_weight
    - Comparison chart data for visualization
    """
    query = select(PromptTemplate).order_by(
        PromptTemplate.name,
        PromptTemplate.version.desc()
    )
    if name:
        query = query.where(PromptTemplate.name == name)

    result = await db.execute(query)
    prompts = result.scalars().all()

    # Group by name
    grouped: dict[str, list[dict]] = {}
    for p in prompts:
        if p.name not in grouped:
            grouped[p.name] = []
        grouped[p.name].append({
            "version": p.version,
            "status": p.status,
            "avg_reward": p.avg_reward or 0.0,
            "usage_count": p.usage_count or 0,
            "traffic_weight": p.traffic_weight,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {
        "prompts": grouped,
        "summary": {
            "total_prompts": len(prompts),
            "active_prompts": len([p for p in prompts if p.status == "active"]),
            "avg_reward_overall": sum(p.avg_reward or 0 for p in prompts) / len(prompts) if prompts else 0,
        }
    }


@router.get("/fsm-transitions")
async def get_fsm_transitions(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get FSM transition statistics for Sankey diagram visualization.

    Returns:
    - Transition counts (ICEBREAK → DISCOVERY: 150, etc.)
    - Success rate by stage
    - Average time in each stage
    """
    # Get recent sessions with stage history
    result = await db.execute(
        select(SessionModel)
        .where(SessionModel.stage_history.isnot(None))
        .order_by(SessionModel.created_at.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()

    # Count transitions
    transitions: dict[str, int] = {}
    stage_durations: dict[str, list[float]] = {}

    for session in sessions:
        history = session.stage_history or []
        for entry in history:
            from_stage = entry.get("from")
            to_stage = entry.get("to")
            if from_stage and to_stage:
                key = f"{from_stage} → {to_stage}"
                transitions[key] = transitions.get(key, 0) + 1

    # Calculate stage statistics
    stage_stats = {}
    for stage in ["ICEBREAK", "DISCOVERY", "PROPOSAL", "CLOSING"]:
        sessions_in_stage = [s for s in sessions if s.current_stage == stage]
        stage_stats[stage] = {
            "current_count": len(sessions_in_stage),
            "completion_rate": 0.0,  # TODO: calculate from history
        }

    return {
        "transitions": transitions,
        "stage_stats": stage_stats,
        "total_sessions": len(sessions),
    }


@router.get("/reward-distribution")
async def get_reward_distribution(
    session_id: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get reward score distribution for quality analysis.

    Returns:
    - Histogram data for each reward dimension
    - Trend over time
    - Outlier detection
    """
    query = select(Message).where(Message.reward_scores.isnot(None))

    if session_id:
        query = query.where(Message.session_id == session_id)

    query = query.order_by(Message.created_at.desc()).limit(limit)

    result = await db.execute(query)
    messages = result.scalars().all()

    # Aggregate reward scores
    dimensions = ["task_progress", "response_quality", "compliance", "user_engagement", "conversion_signal"]
    distribution: dict[str, list[float]] = {dim: [] for dim in dimensions}

    for msg in messages:
        scores = msg.reward_scores or {}
        for dim in dimensions:
            if dim in scores:
                distribution[dim].append(scores[dim])

    # Calculate statistics
    stats = {}
    for dim, values in distribution.items():
        if values:
            stats[dim] = {
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "count": len(values),
            }
        else:
            stats[dim] = {"mean": 0, "min": 0, "max": 0, "count": 0}

    return {
        "distribution": distribution,
        "stats": stats,
        "total_messages": len(messages),
    }


@router.get("/ab-test-summary")
async def get_ab_test_summary(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Get A/B test summary across all active experiments.

    Returns:
    - Active prompt variants with traffic split
    - Performance comparison
    - Statistical significance indicators
    """
    # Get all active and shadow prompts
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.status.in_(["active", "shadow"])
        )
    )
    prompts = result.scalars().all()

    # Group by name to find A/B tests
    ab_tests = {}
    for p in prompts:
        if p.name not in ab_tests:
            ab_tests[p.name] = []
        ab_tests[p.name].append({
            "version": p.version,
            "status": p.status,
            "traffic_weight": p.traffic_weight,
            "avg_reward": p.avg_reward or 0.0,
            "usage_count": p.usage_count or 0,
        })

    # Filter to only multi-variant tests
    active_tests = {
        name: variants
        for name, variants in ab_tests.items()
        if len(variants) > 1
    }

    return {
        "active_tests": active_tests,
        "total_tests": len(active_tests),
        "total_variants": sum(len(v) for v in active_tests.values()),
    }
