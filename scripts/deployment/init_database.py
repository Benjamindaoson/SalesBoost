"""
Database Initialization Script

Creates all tables and initial data.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models import Base, User, UserRole, Course, CourseStatus, Task, TaskStatus
from app.config.unified import get_unified_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database with tables and seed data."""
    settings = get_unified_settings()

    # Create async engine
    engine = create_async_engine(
        settings.database.database_url,
        echo=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Created all database tables")

    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Seed initial data
    async with async_session() as session:
        # Check if data already exists
        from sqlalchemy import select
        result = await session.execute(select(User))
        existing_users = result.scalars().all()

        if existing_users:
            logger.info("Database already seeded, skipping")
            return

        # Create admin user
        admin = User(
            username="admin",
            email="admin@salesboost.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEiUM2",  # "admin123"
            role=UserRole.ADMIN,
            full_name="System Administrator",
            is_active=True,
        )
        session.add(admin)

        # Create demo student
        student = User(
            username="demo",
            email="demo@salesboost.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEiUM2",  # "demo123"
            role=UserRole.STUDENT,
            full_name="Demo Student",
            is_active=True,
        )
        session.add(student)

        # Create sample course
        course = Course(
            title="销售话术基础训练",
            description="学习基本的销售话术和技巧，包括SPIN提问法、FAB法则、异议处理等",
            status=CourseStatus.PUBLISHED,
            category="sales",
            difficulty=1,
            duration_minutes=120,
            instructor_name="AI Coach",
            learning_objectives='["掌握SPIN提问法", "学会FAB产品呈现", "处理常见异议"]',
            tags='["销售", "话术", "基础"]',
        )
        session.add(course)

        await session.commit()

        # Create sample tasks
        task1 = Task(
            course_id=course.id,
            title="开场破冰训练",
            description="练习如何与客户建立初步联系和信任",
            task_type="conversation",
            status=TaskStatus.AVAILABLE,
            order=1,
            points=100,
            passing_score=70.0,
            time_limit_minutes=15,
            instructions="与模拟客户进行开场对话，目标是建立融洽关系",
            scenario='{"product": "信用卡", "customer_type": "price_sensitive"}',
        )
        session.add(task1)

        task2 = Task(
            course_id=course.id,
            title="需求挖掘训练",
            description="使用SPIN提问法挖掘客户需求",
            task_type="conversation",
            status=TaskStatus.LOCKED,
            order=2,
            points=150,
            passing_score=75.0,
            time_limit_minutes=20,
            instructions="使用SPIN提问法（情境、问题、暗示、需求-回报）挖掘客户需求",
            scenario='{"product": "信用卡", "customer_type": "interested"}',
        )
        session.add(task2)

        task3 = Task(
            course_id=course.id,
            title="产品推介训练",
            description="使用FAB法则进行产品推介",
            task_type="conversation",
            status=TaskStatus.LOCKED,
            order=3,
            points=150,
            passing_score=75.0,
            time_limit_minutes=20,
            instructions="使用FAB法则（特征-优势-利益）进行产品推介",
            scenario='{"product": "信用卡", "customer_type": "interested"}',
        )
        session.add(task3)

        task4 = Task(
            course_id=course.id,
            title="异议处理训练",
            description="处理客户的常见异议",
            task_type="conversation",
            status=TaskStatus.LOCKED,
            order=4,
            points=200,
            passing_score=80.0,
            time_limit_minutes=25,
            instructions="处理客户的价格、信任等异议",
            scenario='{"product": "信用卡", "customer_type": "skeptical"}',
        )
        session.add(task4)

        await session.commit()

        logger.info("Database seeded successfully")
        logger.info("Admin user: admin / admin123")
        logger.info("Demo user: demo / demo123")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())
