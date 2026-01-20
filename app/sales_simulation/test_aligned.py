"""
对齐验证测试
验证 Simulation 与主系统 FSM 完全对齐
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


async def test_fsm_consistency_validation():
    """测试 FSM 一致性验证"""
    logger.info("="*70)
    logger.info("Test 1: FSM Consistency Validation")
    logger.info("="*70)
    
    from app.sales_simulation.validation import FSMConsistencyValidator
    
    try:
        # 启动时验证
        FSMConsistencyValidator.validate_simulation_startup()
        logger.info("✅ FSM consistency validation passed")
        
        # 获取一致性报告
        report = FSMConsistencyValidator.get_consistency_report()
        logger.info(f"Consistency report: {report}")
        
        return True
    except Exception as e:
        logger.error(f"❌ FSM consistency validation failed: {e}")
        return False


async def test_decision_engine_adapter():
    """测试 DecisionEngine Adapter"""
    logger.info("\n" + "="*70)
    logger.info("Test 2: DecisionEngine Adapter")
    logger.info("="*70)
    
    from app.sales_simulation.adapters.decision_engine_adapter import DecisionEngineAdapter
    from app.fsm.protocol import SalesFSMState
    
    try:
        # 创建 Adapter
        adapter = DecisionEngineAdapter()
        logger.info("✅ DecisionEngineAdapter created")
        
        # 创建初始 FSM State
        fsm_state = adapter.create_initial_fsm_state()
        logger.info(f"✅ Initial FSM state: {fsm_state.current_stage.value}")
        
        # 验证初始状态
        assert fsm_state.current_stage.value == SalesFSMState.OPENING.value
        logger.info("✅ Initial state is OPENING")
        
        # 模拟一步决策
        observation = {
            "customer_response": "你好",
            "customer_mood": 0.5,
            "customer_interest": 0.4,
            "current_stage": "OPENING",
            "goal_progress": 0.1,
            "detected_signals": [],
            "step_score": 0.7,
            "mood_before": 0.45,
        }
        
        updated_state, decision = await adapter.decide_next_state(
            current_fsm_state=fsm_state,
            simulation_observation=observation,
            current_turn=1,
        )
        
        logger.info(f"✅ DecisionEngine called successfully")
        logger.info(f"  Decision: should_transition={decision.should_transition}")
        logger.info(f"  From: {decision.from_stage.value}")
        logger.info(f"  To: {decision.to_stage.value if decision.to_stage else 'N/A'}")
        logger.info(f"  Reason: {decision.reason}")
        
        return True
    except Exception as e:
        logger.error(f"❌ DecisionEngine Adapter test failed: {e}", exc_info=True)
        return False


async def test_state_manager_alignment():
    """测试 StateManager 对齐"""
    logger.info("\n" + "="*70)
    logger.info("Test 3: StateManager Alignment")
    logger.info("="*70)
    
    from app.sales_simulation.scenarios.loader import ScenarioLoader
    from app.sales_simulation.environment.state_manager import StateManager
    from app.fsm.protocol import SalesFSMState
    
    try:
        # 加载场景
        loader = ScenarioLoader()
        scenario = loader.load_scenario("scenario_001_cold_call")
        
        # 创建 StateManager
        state_manager = StateManager(scenario)
        logger.info("✅ StateManager created")
        
        # 验证初始状态
        assert state_manager.current_stage == "OPENING"
        logger.info(f"✅ Initial stage: {state_manager.current_stage}")
        
        # 测试应用状态转换
        state_manager.apply_stage_transition("NEEDS_DISCOVERY")
        assert state_manager.current_stage == "NEEDS_DISCOVERY"
        logger.info("✅ Stage transition applied: OPENING -> NEEDS_DISCOVERY")
        
        # 测试非法状态检测
        try:
            state_manager.apply_stage_transition("INVALID_STATE")
            logger.error("❌ Should have raised ValueError for invalid state")
            return False
        except ValueError as e:
            logger.info(f"✅ Invalid state correctly rejected: {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ StateManager alignment test failed: {e}", exc_info=True)
        return False


async def test_aligned_environment():
    """测试对齐环境"""
    logger.info("\n" + "="*70)
    logger.info("Test 4: Aligned Environment")
    logger.info("="*70)
    
    from app.sales_simulation.scenarios.loader import ScenarioLoader
    from app.sales_simulation.environment.sales_env_aligned import AlignedSalesSimulationEnv
    from app.sales_simulation.schemas.trajectory import StepAction, ActionType
    
    try:
        # 加载场景
        loader = ScenarioLoader()
        scenario = loader.load_scenario("scenario_001_cold_call")
        
        # 创建对齐环境
        env = AlignedSalesSimulationEnv(scenario)
        logger.info("✅ AlignedSalesSimulationEnv created")
        
        # 重置环境
        obs = env.reset(seed=42)
        logger.info(f"✅ Environment reset, initial stage: {obs.current_stage}")
        
        # 执行几步（使用异步版本）
        for i in range(3):
            action = StepAction(
                action_type=ActionType.QUESTION,
                content=f"测试动作 {i+1}",
                reasoning="测试",
                confidence=0.9,
            )
            
            obs, reward, done, info = await env.step_async(action)
            logger.info(f"✅ Step {i+1}: stage={obs.current_stage}, reward={reward:.2f}, done={done}")
            logger.info(f"  FSM state from info: {info.get('fsm_state')}")
            
            if done:
                break
        
        logger.info("✅ Aligned environment test completed")
        return True
    except Exception as e:
        logger.error(f"❌ Aligned environment test failed: {e}", exc_info=True)
        return False


async def main():
    """主测试流程"""
    logger.info("\n" + "="*70)
    logger.info("SalesBoost 系统对齐验证测试")
    logger.info("="*70)
    
    results = []
    
    # Test 1: FSM 一致性验证
    results.append(await test_fsm_consistency_validation())
    
    # Test 2: DecisionEngine Adapter
    results.append(await test_decision_engine_adapter())
    
    # Test 3: StateManager 对齐
    results.append(await test_state_manager_alignment())
    
    # Test 4: 对齐环境
    results.append(await test_aligned_environment())
    
    # 总结
    logger.info("\n" + "="*70)
    logger.info("测试总结")
    logger.info("="*70)
    
    passed = sum(results)
    total = len(results)
    
    logger.info(f"通过: {passed}/{total}")
    
    if passed == total:
        logger.info("✅ 所有测试通过！系统对齐成功！")
        return 0
    else:
        logger.error(f"❌ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

