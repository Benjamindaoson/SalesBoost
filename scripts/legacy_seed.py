"""
冷启动数据脚本 - Seed Data
幂等性设计：检查数据是否存在，避免重复插入
"""
import asyncio
import uuid
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import async_session_factory, init_db
from app.models.config_models import Course, ScenarioConfig, CustomerPersona

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 预定义 ID（便于测试客户端使用）
COURSE_ID = "course-credit-card-001"
SCENARIO_ID = "scenario-annual-fee-001"
PERSONA_ID = "persona-wang-001"


async def seed_course(session) -> Course:
    """插入课程数据"""
    result = await session.execute(
        select(Course).where(Course.id == COURSE_ID)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        logger.info(f"Course already exists: {existing.name}")
        return existing
    
    course = Course(
        id=COURSE_ID,
        name="白金卡销售实战",
        description="高端信用卡销售技巧训练，包含年费异议处理、权益介绍、促单成交等核心场景",
        product_category="信用卡",
        difficulty_level="advanced",
        estimated_duration_minutes=45,
        is_active=True,
        tags=["信用卡", "高端客户", "异议处理", "年费"],
        prerequisites=["基础销售技巧"],
        learning_objectives=[
            "掌握高端信用卡价值传递技巧",
            "学会处理年费异议的 Feel-Felt-Found 方法",
            "提升促单成交能力",
        ],
    )
    session.add(course)
    await session.flush()
    logger.info(f"Course created: {course.name}")
    return course


async def seed_scenario(session, course_id: str) -> ScenarioConfig:
    """插入场景配置"""
    result = await session.execute(
        select(ScenarioConfig).where(ScenarioConfig.id == SCENARIO_ID)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        logger.info(f"Scenario already exists: {existing.name}")
        return existing
    
    scenario = ScenarioConfig(
        id=SCENARIO_ID,
        course_id=course_id,
        name="年费异议处理",
        description="客户对 3600 元年费提出异议，销售需要通过价值传递化解异议并挽留客户",
        product_category="信用卡",
        scenario_background="客户王总是一位企业主，持有白金卡已满一年，来电表示年费太贵想要销卡",
        sales_goal="成功挽留客户，让客户认可年费价值并继续持卡",
        success_criteria={
            "must_achieve": ["客户放弃销卡", "客户认可至少一项权益价值"],
            "bonus": ["客户主动询问其他权益", "客户表示会推荐给朋友"],
        },
        stage_configs={},
        max_turns=15,
        difficulty_level="advanced",
        customer_difficulty=0.7,
        is_active=True,
    )
    session.add(scenario)
    await session.flush()
    logger.info(f"Scenario created: {scenario.name}")
    return scenario


async def seed_persona(session, scenario_id: str) -> CustomerPersona:
    """插入客户人设"""
    result = await session.execute(
        select(CustomerPersona).where(CustomerPersona.id == PERSONA_ID)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        logger.info(f"Persona already exists: {existing.name}")
        return existing
    
    persona = CustomerPersona(
        id=PERSONA_ID,
        scenario_id=scenario_id,
        name="王总",
        occupation="企业主",
        age_range="40-50",
        gender="male",
        personality_traits="精明、价格敏感、注重实际价值、不喜欢被忽悠",
        communication_style="直接、简洁、喜欢看数据和事实",
        decision_style="理性决策、需要充分理由",
        buying_motivation="商旅出行便利、身份象征",
        main_concerns="觉得 3600 元年费太贵，且权益用不上",
        budget_sensitivity="高",
        initial_mood=0.4,
        mood_volatility=0.3,
        difficulty_level="advanced",
        objection_frequency=0.6,
        is_active=True,
    )
    session.add(persona)
    await session.flush()
    logger.info(f"Persona created: {persona.name}")
    return persona


async def main():
    """主函数 - 执行数据初始化"""
    logger.info("=" * 50)
    logger.info("SalesBoost Cold Start - Seed Data")
    logger.info("=" * 50)
    
    # 初始化数据库表
    logger.info("Initializing database tables...")
    await init_db()
    
    # 插入种子数据
    async with async_session_factory() as session:
        try:
            # 1. 创建课程
            course = await seed_course(session)
            
            # 2. 创建场景
            scenario = await seed_scenario(session, course.id)
            
            # 3. 创建人设
            persona = await seed_persona(session, scenario.id)
            
            # 提交事务
            await session.commit()
            
            logger.info("=" * 50)
            logger.info("Seed data completed successfully!")
            logger.info(f"Course ID: {course.id}")
            logger.info(f"Scenario ID: {scenario.id}")
            logger.info(f"Persona ID: {persona.id}")
            logger.info("=" * 50)
            logger.info("")
            logger.info("WebSocket Test URL:")
            logger.info(f"ws://localhost:8000/ws/train?course_id={course.id}&scenario_id={scenario.id}&persona_id={persona.id}&user_id=test-user-001")
            logger.info("")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Seed data failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
