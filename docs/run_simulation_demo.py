"""
Sales Simulation Demo Script
运行单智能体仿真演示，验证 P0 流程

Usage:
    python scripts/run_simulation_demo.py
"""
import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.sales_simulation.config import SimulationConfig
from app.sales_simulation.agents.dialogue_agent import DialogueAgent
from app.sales_simulation.runners.single_agent_runner import (
    SingleAgentSimulationRunner,
    SimulationResult,
    AgentUnderTest
)
from app.sales_simulation.schemas.scenario import (
    SimulationScenario,
    ScenarioConfig,
    CustomerProfile,
    SalesGoal,
    CustomerType,
    DifficultyLevel
)
from app.sales_simulation.schemas.trajectory import (
    StepAction,
    StepObservation,
    ActionType
)
from core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DialogueAgentAdapter(AgentUnderTest):
    """
    DialogueAgent适配器
    将DialogueAgent适配为SingleAgentSimulationRunner需要的接口
    """
    
    def __init__(self, dialogue_agent: DialogueAgent, scenario: SimulationScenario):
        self.dialogue_agent = dialogue_agent
        self.scenario = scenario
        self._current_stage = "OPENING"
    
    async def act(
        self,
        observation: StepObservation,
        history: List[Dict[str, Any]]
    ) -> StepAction:
        """
        根据观察和历史生成动作
        
        Args:
            observation: 当前观察
            history: 对话历史
            
        Returns:
            动作对象
        """
        # 更新当前阶段
        self._current_stage = observation.current_stage
        
        # 确定动作类型（基于当前阶段和观察）
        action_type = self._determine_action_type(observation, history)
        
        # 构建当前状态
        current_state = {
            "customer_mood": observation.customer_mood,
            "customer_interest": observation.customer_interest,
            "current_stage": observation.current_stage,
            "goal_progress": observation.goal_progress,
        }
        
        # 构建对话历史（转换为DialogueAgent需要的格式）
        # history格式: [{"role": "user", "content": "...", "turn": 1}, {"role": "npc", "content": "...", "turn": 1}, ...]
        conversation_history = []
        agent_turn = None
        
        for h in history[-6:]:  # 取最近6条（3轮对话）
            role = h.get("role", "")
            content = h.get("content", "")
            turn = h.get("turn", 0)
            
            if role == "user":
                # Agent说的话，开始新的一轮
                agent_turn = {
                    "step": turn,
                    "agent": content,
                    "customer": ""
                }
            elif role == "npc" and agent_turn:
                # Customer说的话，完成当前轮
                agent_turn["customer"] = content
                conversation_history.append(agent_turn)
                agent_turn = None
        
        # 如果最后一轮只有agent没有customer，也添加
        if agent_turn:
            conversation_history.append(agent_turn)
        
        # 构建客户画像
        customer_profile = {
            "name": self.scenario.customer_profile.name,
            "role": self.scenario.customer_profile.role,
            "decision_style": self.scenario.customer_profile.decision_style,
            "personality_traits": self.scenario.customer_profile.personality_traits,
        }
        
        # 生成对话
        try:
            dialogue_output = await self.dialogue_agent.generate_dialogue(
                action_type=action_type.value if isinstance(action_type, ActionType) else action_type,
                current_state=current_state,
                conversation_history=conversation_history,
                customer_profile=customer_profile,
            )
            
            # 构建动作
            action = StepAction(
                action_type=action_type,
                content=dialogue_output.content,
                reasoning=f"Generated dialogue with {dialogue_output.tone} tone",
                confidence=dialogue_output.confidence,
            )
            
            return action
            
        except Exception as e:
            logger.error(f"Failed to generate dialogue: {e}")
            # 降级处理
            return StepAction(
                action_type=action_type,
                content="让我为您介绍一下我们的解决方案。",
                reasoning="Fallback dialogue",
                confidence=0.5,
            )
    
    def _determine_action_type(
        self,
        observation: StepObservation,
        history: List[Dict[str, Any]]
    ) -> ActionType:
        """
        根据观察和历史确定动作类型
        
        Args:
            observation: 当前观察
            history: 对话历史
            
        Returns:
            动作类型
        """
        stage = observation.current_stage
        
        # 基于阶段的简单策略
        if stage == "OPENING":
            if not history:
                return ActionType.QUESTION  # 开场提问
            return ActionType.SPEAK
        elif stage == "NEEDS_DISCOVERY":
            return ActionType.QUESTION  # 需求挖掘
        elif stage == "PRESENTATION":
            return ActionType.PRESENT  # 产品展示
        elif stage == "OBJECTION_HANDLING":
            return ActionType.HANDLE_OBJECTION  # 处理异议
        elif stage == "CLOSING":
            return ActionType.CLOSE  # 促单
        else:
            # 默认动作
            if observation.customer_mood < 0.3:
                return ActionType.LISTEN  # 客户情绪低，先倾听
            elif observation.goal_progress > 0.8:
                return ActionType.CLOSE  # 目标进度高，尝试促单
            else:
                return ActionType.SPEAK  # 默认说话


def create_dummy_scenario() -> SimulationScenario:
    """
    创建演示用的场景配置
    
    Returns:
        仿真场景
    """
    scenario = SimulationScenario(
        id="demo_scenario_001",
        name="演示场景 - 冷呼销售",
        description="演示单智能体仿真流程",
        difficulty=DifficultyLevel.MEDIUM,
        customer_profile=CustomerProfile(
            name="张总",
            company="示例科技公司",
            role="技术总监",
            customer_type=CustomerType.COLD_LEAD,
            personality_traits=["理性", "谨慎"],
            pain_points=["团队协作效率低", "工具分散"],
            objections=["价格太贵", "担心学习成本"],
            decision_style="analytical",
            budget_sensitivity=0.7,
            urgency_level=0.4,
            initial_mood=0.4,
            initial_interest=0.3,
        ),
        sales_goal=SalesGoal(
            goal_type="demo",
            success_criteria=[
                "客户同意参加产品演示",
                "确认具体时间",
            ]
        ),
        config=ScenarioConfig(
            max_turns=3,  # 演示用，只运行3轮
            timeout_seconds=300,
            enable_interruption=True,
            enable_emotion_drift=True,
            enable_random_events=False,
        ),
        background_context="客户公司正在快速扩张，团队协作工具老旧，正在评估新方案",
        product_info={
            "name": "协作云平台",
            "category": "SaaS",
            "price_range": "5000-20000/月"
        },
        tags=["demo", "cold_call"],
    )
    
    return scenario


def print_simulation_result(result: SimulationResult):
    """
    打印仿真结果
    
    Args:
        result: 仿真结果
    """
    print("\n" + "="*80)
    print("SIMULATION RESULT")
    print("="*80)
    print(f"Episode ID: {result.episode_id}")
    print(f"Trajectory ID: {result.trajectory_id}")
    print(f"Total Steps: {result.total_steps}")
    print(f"Total Reward: {result.total_reward:.2f}")
    print(f"Successful Sale: {'✅ YES' if result.successful_sale else '❌ NO'}")
    print(f"Duration: {result.duration_seconds:.2f} seconds")
    print(f"Status: {result.trajectory.status.value}")
    print("="*80)
    
    # 打印对话轨迹
    print("\n" + "="*80)
    print("CONVERSATION TRAJECTORY")
    print("="*80)
    
    for i, step in enumerate(result.trajectory.steps, 1):
        print(f"\n--- Turn {i} ---")
        print(f"🤖 Agent ({step.action.action_type.value}):")
        print(f"   {step.action.content}")
        if step.action.reasoning:
            print(f"   💭 Reasoning: {step.action.reasoning}")
        print(f"   📊 Confidence: {step.action.confidence:.2f}")
        
        print(f"\n👤 Customer Response:")
        print(f"   {step.observation.customer_response}")
        print(f"   😊 Mood: {step.observation.customer_mood:.2f}")
        print(f"   💡 Interest: {step.observation.customer_interest:.2f}")
        print(f"   📍 Stage: {step.observation.current_stage}")
        print(f"   🎯 Goal Progress: {step.observation.goal_progress:.2f}")
        print(f"   ⭐ Step Reward: {step.step_reward:.2f}")
        print(f"   📈 Step Score: {step.step_score:.2f}")
    
    print("\n" + "="*80)
    print("TRAJECTORY SUMMARY")
    print("="*80)
    print(f"Total Steps: {result.trajectory.total_steps}")
    print(f"Total Reward: {result.trajectory.total_reward:.2f}")
    print(f"Goal Achieved: {'✅ YES' if result.trajectory.goal_achieved else '❌ NO'}")
    print(f"Duration: {result.trajectory.duration_seconds:.2f}s")
    print("="*80 + "\n")


async def main():
    """
    主函数：运行仿真演示
    """
    # 检查环境变量
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        print("❌ ERROR: OPENAI_API_KEY not set in environment")
        print("Please set it with: export OPENAI_API_KEY=your_key")
        sys.exit(1)
    
    print("🚀 Starting Sales Simulation Demo")
    print(f"Using OpenAI API: {settings.OPENAI_BASE_URL or 'default'}")
    print(f"Model: {settings.OPENAI_MODEL}")
    
    try:
        # 1. 创建配置
        print("\n📋 Step 1: Creating simulation config...")
        config = SimulationConfig(
            DEFAULT_MAX_TURNS=3,
            DEFAULT_SEED=42,
        )
        print(f"   Max turns: {config.DEFAULT_MAX_TURNS}")
        print(f"   Seed: {config.DEFAULT_SEED}")
        
        # 2. 创建场景
        print("\n📋 Step 2: Creating scenario...")
        scenario = create_dummy_scenario()
        print(f"   Scenario ID: {scenario.id}")
        print(f"   Scenario Name: {scenario.name}")
        print(f"   Customer: {scenario.customer_profile.name} ({scenario.customer_profile.role})")
        print(f"   Goal: {scenario.sales_goal.goal_type}")
        print(f"   Max Turns: {scenario.config.max_turns}")
        
        # 3. 初始化DialogueAgent
        print("\n📋 Step 3: Initializing DialogueAgent...")
        dialogue_agent = DialogueAgent()
        print("   ✅ DialogueAgent initialized")
        
        # 4. 创建适配器
        print("\n📋 Step 4: Creating agent adapter...")
        agent = DialogueAgentAdapter(dialogue_agent, scenario)
        print("   ✅ Agent adapter created")
        
        # 5. 初始化运行器
        print("\n📋 Step 5: Initializing simulation runner...")
        runner = SingleAgentSimulationRunner(
            config=config,
            agent=agent,
            scenario=scenario
        )
        print("   ✅ Runner initialized")
        
        # 6. 运行仿真
        print("\n🎬 Step 6: Running simulation episode...")
        print("   Episode ID: test_run_001")
        print("-" * 80)
        
        result = await runner.run_episode(episode_id="test_run_001", seed=42)
        
        # 7. 打印结果
        print_simulation_result(result)
        
        print("✅ Simulation demo completed successfully!")
        
    except Exception as e:
        logger.exception("Simulation demo failed")
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

