import uuid
from datetime import datetime

import pytest
from sqlalchemy import select

from core.database import async_session_factory
from models.config_models import Course, ScenarioConfig, CustomerPersona
from models.runtime_models import Session
from models.adoption_models import StrategyDecision
from cognitive.skills.coordination.orchestrator import SessionOrchestrator


COURSE_ID = "course-credit-card-001"
SCENARIO_ID = "scenario-annual-fee-001"
PERSONA_ID = "persona-wang-001"


@pytest.mark.asyncio
async def test_e2e_turn_loop():
    async with async_session_factory() as db:
        course = await _get_or_create_course(db)
        scenario = await _get_or_create_scenario(db, course.id)
        persona = await _get_or_create_persona(db, scenario.id)

        session_id = str(uuid.uuid4())
        user_id = "test-user-e2e"
        runtime_session = Session(
            id=session_id,
            user_id=user_id,
            course_id=course.id,
            scenario_id=scenario.id,
            persona_id=persona.id,
            status="active",
            started_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
            total_turns=0,
            total_duration_seconds=0,
        )
        db.add(runtime_session)
        await db.commit()

        orchestrator = SessionOrchestrator(
            scenario_config=scenario,
            customer_persona=persona,
        )
        await orchestrator.initialize_session(session_id=session_id, user_id=user_id)

        result = await orchestrator.process_turn(
            user_message="王总您好，我想帮您看看年费有没有更合适的方案。",
            session=runtime_session,
            db=db,
        )

        assert result.turn_number == 1
        assert result.npc_result.response
        assert result.coach_result.suggestion
        assert result.evaluator_result.overall_score is not None

        decision_count = await _count_strategy_decisions(db, session_id)
        assert decision_count >= 1


async def _get_or_create_course(db):
    result = await db.execute(select(Course).where(Course.id == COURSE_ID))
    course = result.scalar_one_or_none()
    if course:
        return course

    course = Course(
        id=COURSE_ID,
        name="白金卡销售实战",
        description="年费异议处理",
        product_category="信用卡",
        difficulty_level="beginner",
    )
    db.add(course)
    await db.commit()
    return course


async def _get_or_create_scenario(db, course_id: str):
    result = await db.execute(select(ScenarioConfig).where(ScenarioConfig.id == SCENARIO_ID))
    scenario = result.scalar_one_or_none()
    if scenario:
        return scenario

    scenario = ScenarioConfig(
        id=SCENARIO_ID,
        course_id=course_id,
        name="年费异议处理",
        description="客户对年费敏感，需要价值重塑",
        product_category="信用卡",
        scenario_background="客户希望销卡，关注年费成本。",
        sales_goal="提升客户对年费价值的认可",
        max_turns=10,
    )
    db.add(scenario)
    await db.commit()
    return scenario


async def _get_or_create_persona(db, scenario_id: str):
    result = await db.execute(select(CustomerPersona).where(CustomerPersona.id == PERSONA_ID))
    persona = result.scalar_one_or_none()
    if persona:
        return persona

    persona = CustomerPersona(
        id=PERSONA_ID,
        scenario_id=scenario_id,
        name="王总",
        occupation="企业主",
        personality_traits="谨慎、关注成本",
        main_concerns="年费太高",
        initial_mood=0.4,
    )
    db.add(persona)
    await db.commit()
    return persona


async def _count_strategy_decisions(db, session_id: str) -> int:
    result = await db.execute(
        select(StrategyDecision).where(StrategyDecision.session_id == session_id)
    )
    return len(result.scalars().all())
