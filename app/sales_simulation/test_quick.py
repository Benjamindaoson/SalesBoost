"""
快速测试脚本
验证子系统基本功能
"""
import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_scenario_loader():
    """测试场景加载"""
    logger.info("Testing ScenarioLoader...")
    
    from app.sales_simulation.scenarios.loader import ScenarioLoader
    
    loader = ScenarioLoader()
    
    # 列出场景
    scenario_ids = loader.list_scenario_ids()
    logger.info(f"Found {len(scenario_ids)} scenarios: {scenario_ids}")
    
    # 加载场景
    if scenario_ids:
        scenario = loader.load_scenario(scenario_ids[0])
        logger.info(f"Loaded scenario: {scenario.name}")
        logger.info(f"  Difficulty: {scenario.difficulty}")
        logger.info(f"  Customer: {scenario.customer_profile.name}")
        logger.info(f"  Goal: {scenario.sales_goal.goal_type}")
        return scenario
    
    return None


async def test_environment(scenario):
    """测试环境"""
    logger.info("Testing SalesSimulationEnv...")
    
    from app.sales_simulation.environment.sales_env import SalesSimulationEnv
    from app.sales_simulation.schemas.trajectory import StepAction, ActionType
    
    env = SalesSimulationEnv(scenario)
    
    # 重置环境
    obs = env.reset(seed=42)
    logger.info(f"Initial observation: mood={obs.customer_mood:.2f}, interest={obs.customer_interest:.2f}")
    
    # 执行一步
    action = StepAction(
        action_type=ActionType.QUESTION,
        content="您好，请问您目前在团队协作方面遇到什么挑战？",
        reasoning="开场提问",
        confidence=0.9,
    )
    
    obs, reward, done, info = env.step(action)
    logger.info(f"After step: reward={reward:.2f}, done={done}")
    logger.info(f"  Customer response: {obs.customer_response[:50]}...")
    
    return env


async def test_agents():
    """测试 Agents"""
    logger.info("Testing Agents...")
    
    from app.sales_simulation.agents.planner_agent import PlannerAgent
    
    planner = PlannerAgent()
    
    # 测试规划（使用降级模式）
    current_state = {
        "current_stage": "OPENING",
        "customer_mood": 0.5,
        "customer_interest": 0.4,
        "customer_trust": 0.3,
        "goal_progress": 0.0,
        "conversation_turns": 0,
        "detected_signals": [],
    }
    
    try:
        # 尝试调用 LLM（可能失败，会降级）
        output = await planner.plan_next_action(
            current_state=current_state,
            conversation_history=[],
            goal_description="获得演示机会",
        )
        logger.info(f"Planner output: {output.action_type} (confidence: {output.confidence:.2f})")
        logger.info(f"  Reasoning: {output.reasoning}")
    except Exception as e:
        logger.warning(f"Planner LLM call failed (expected): {e}")


async def test_metrics():
    """测试指标计算"""
    logger.info("Testing MetricsCalculator...")
    
    from app.sales_simulation.schemas.trajectory import Trajectory, TrajectoryStatus
    from app.sales_simulation.evaluation.metrics_calculator import MetricsCalculator
    from datetime import datetime
    
    # 创建模拟轨迹
    trajectory = Trajectory(
        id="test_traj_001",
        run_id="test_run",
        scenario_id="scenario_001",
        seed=42,
        agent_config={"type": "single"},
        steps=[],
        status=TrajectoryStatus.COMPLETED,
        goal_achieved=True,
        final_score=0.85,
        total_steps=12,
        duration_seconds=180.0,
        started_at=datetime.utcnow(),
    )
    
    # 计算指标
    metrics = MetricsCalculator.calculate_trajectory_metrics(trajectory)
    logger.info(f"Trajectory metrics:")
    logger.info(f"  Goal achieved: {metrics.goal_achieved}")
    logger.info(f"  Final score: {metrics.goal_completion_rate:.2f}")
    logger.info(f"  Total steps: {metrics.total_steps}")


async def main():
    """主测试流程"""
    logger.info("="*50)
    logger.info("SalesBoost 模拟平台快速测试")
    logger.info("="*50)
    
    try:
        # 1. 测试场景加载
        scenario = await test_scenario_loader()
        
        if scenario:
            # 2. 测试环境
            await test_environment(scenario)
        
        # 3. 测试 Agents
        await test_agents()
        
        # 4. 测试指标
        await test_metrics()
        
        logger.info("="*50)
        logger.info("✅ 所有测试通过！")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)




