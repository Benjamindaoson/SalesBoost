"""
种子数据脚本 - 创建初始测试数据
用于快速填充数据库，方便测试和演示

运行方式:
cd backend
python scripts/seed_data.py

Mock 数据统一存放在 app.data.seed_constants，供 API 使用。
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session, init_db
from app.models.course import Course, CourseStatus
from app.models.task import Task, TaskStatus


async def create_seed_data():
    """创建种子数据"""
    print("=" * 70)
    print("开始创建种子数据...")
    print("=" * 70)

    # 初始化数据库（创建表）
    print("\n[数据库] 初始化数据库表...")
    await init_db()
    print("  [OK] 数据库表创建成功")

    async for db in get_db_session():
        try:
            # ==================== 创建课程 ====================
            print("\n[课程] 创建课程...")

            course1 = Course(
                title="新客户开发训练",
                description="学习如何有效地开发新客户，掌握开场白、需求挖掘和异议处理技巧",
                difficulty=1,
                duration_minutes=120,
                status=CourseStatus.PUBLISHED,
                category="sales"
            )
            db.add(course1)
            await db.flush()  # 获取 ID

            course2 = Course(
                title="高级销售技巧",
                description="提升销售能力，学习高级谈判技巧和成交策略",
                difficulty=3,
                duration_minutes=240,
                status=CourseStatus.PUBLISHED,
                category="sales"
            )
            db.add(course2)
            await db.flush()

            print(f"  [OK] 创建了 2 个课程 (ID: {course1.id}, {course2.id})")

            # ==================== 创建任务 ====================
            print("\n[任务] 创建任务...")

            task1 = Task(
                course_id=course1.id,
                title="新客户开场白训练",
                description="练习与新客户的第一次接触，学习如何建立良好的第一印象",
                task_type="conversation",
                status=TaskStatus.AVAILABLE,
                order=1,
                points=100,
                passing_score=70.0,
                time_limit_minutes=30,
                instructions="在这个任务中，你将扮演销售代表，与一位新客户进行首次接触。请注意：\n1. 保持专业和友好的态度\n2. 清晰地介绍自己和公司\n3. 了解客户的基本需求\n4. 建立信任关系"
            )
            db.add(task1)

            task2 = Task(
                course_id=course1.id,
                title="需求挖掘训练",
                description="学习如何深入了解客户需求，发现潜在机会",
                task_type="conversation",
                status=TaskStatus.AVAILABLE,
                order=2,
                points=120,
                passing_score=75.0,
                time_limit_minutes=40,
                instructions="通过有效的提问技巧，深入了解客户的真实需求和痛点"
            )
            db.add(task2)

            task3 = Task(
                course_id=course1.id,
                title="异议处理训练",
                description="学习如何处理客户的异议和疑虑",
                task_type="conversation",
                status=TaskStatus.LOCKED,
                order=3,
                points=150,
                passing_score=75.0,
                time_limit_minutes=45,
                instructions="客户可能会提出各种异议，学习如何专业地回应和解决"
            )
            db.add(task3)

            task4 = Task(
                course_id=course2.id,
                title="高级谈判技巧",
                description="掌握高级谈判策略，实现双赢结果",
                task_type="simulation",
                status=TaskStatus.AVAILABLE,
                order=1,
                points=200,
                passing_score=80.0,
                time_limit_minutes=60,
                instructions="在复杂的商务谈判中，运用高级技巧达成协议"
            )
            db.add(task4)

            task5 = Task(
                course_id=course2.id,
                title="成交策略训练",
                description="学习如何识别成交信号并推动交易完成",
                task_type="conversation",
                status=TaskStatus.LOCKED,
                order=2,
                points=180,
                passing_score=80.0,
                time_limit_minutes=50,
                instructions="掌握成交的最佳时机和策略"
            )
            db.add(task5)

            print("  [OK] 创建了 5 个任务")

            # 提交所有更改
            await db.commit()

            print("\n" + "=" * 70)
            print("[成功] 种子数据创建成功！")
            print("=" * 70)
            print("\n[统计] 数据统计:")
            print(f"  - 课程: 2 个")
            print(f"  - 任务: 5 个")
            print("\n[启动] 现在可以启动应用并查看数据了！")
            print("   后端: cd backend && python main.py")
            print("   前端: cd frontend && npm run dev")
            print("\n[访问] 打开浏览器访问:")
            print("   http://localhost:5173/student/dashboard")
            print()

        except Exception as e:
            print(f"\n[错误] 创建种子数据失败: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            raise


if __name__ == "__main__":
    # 设置 UTF-8 编码
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("\n[SalesBoost] 种子数据生成器")
    print("=" * 70)
    asyncio.run(create_seed_data())
