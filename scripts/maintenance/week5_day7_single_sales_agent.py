"""
Phase 3B Week 5 Day 7: Single Sales Agent - Complete Integration

核心目标：将 FSM、SPIN & FAB、Intent Routing 完整集成，构建一个具备专业销售逻辑的对话 Agent。

实现日期: 2026-02-02
"""

import logging
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.agents.conversation import (
    SalesState,
    TransitionTrigger,
    ConversationContext,
    SalesConversationFSM,
    PromptManager,
    UserIntent,
    IntentRouter,
    ActionRouter
)

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Agent 响应"""
    content: str
    current_state: str
    intent_detected: str
    rag_used: bool
    state_changed: bool
    metadata: Dict[str, Any]


class SingleSalesAgent:
    """
    单一销售 Agent

    Phase 3B Week 5 完整交付物

    核心功能：
    1. 状态管理：使用 FSM 跟踪对话状态
    2. 意图识别：使用 IntentRouter 分析用户意图
    3. 动态 RAG：根据意图决定是否调用知识库
    4. 方法论指导：使用 SPIN & FAB 生成专业话术
    5. 状态转换：根据对话进展自动转换状态
    """

    def __init__(self, knowledge_interface=None, model_gateway=None):
        """
        初始化 Agent

        Args:
            knowledge_interface: Phase 3A 的知识接口
            model_gateway: LLM 调用网关
        """
        self.fsm = SalesConversationFSM()
        self.prompt_manager = PromptManager()
        self.action_router = ActionRouter(knowledge_interface=knowledge_interface)
        self.model_gateway = model_gateway

        # 会话存储
        self.sessions: Dict[str, ConversationContext] = {}

        logger.info("SingleSalesAgent initialized")

    def get_or_create_session(self, session_id: str) -> ConversationContext:
        """获取或创建会话上下文"""
        if session_id not in self.sessions:
            self.sessions[session_id] = self.fsm.create_context(session_id)
            logger.info(f"Created new session: {session_id}")
        return self.sessions[session_id]

    async def process_message(
        self,
        session_id: str,
        message: str
    ) -> AgentResponse:
        """
        处理用户消息

        核心流程：
        1. 获取会话上下文
        2. 分析用户意图
        3. 决定是否调用 RAG
        4. 生成 System Prompt
        5. 调用 LLM 生成响应
        6. 更新状态和上下文
        7. 返回响应

        Args:
            session_id: 会话 ID
            message: 用户消息

        Returns:
            AgentResponse: Agent 响应
        """
        # 1. 获取会话上下文
        context = self.get_or_create_session(session_id)
        old_state = context.current_state

        # 记录用户消息
        context.history.append({"role": "user", "content": message})

        # 2. 分析用户意图
        action = await self.action_router.route_action(message, context.to_dict())

        intent = action["intent"]
        requires_rag = action["requires_rag"]
        rag_results = action.get("rag_results")

        logger.info(
            f"Session {session_id}: Intent={intent}, "
            f"State={context.current_state.value}, RAG={requires_rag}"
        )

        # 3. 根据意图更新状态
        state_changed = self._update_state_by_intent(context, intent, message)

        # 4. 生成 System Prompt
        system_prompt = self._generate_system_prompt(context, rag_results)

        # 5. 生成响应
        if self.model_gateway:
            # 调用 LLM
            response_content = await self._call_llm(system_prompt, message, context)
        else:
            # 使用推荐响应（测试模式）
            response_content = action.get("recommended_response", "")
            if not response_content:
                response_content = self._generate_fallback_response(context, intent)

        # 6. 记录 Agent 响应
        context.history.append({"role": "assistant", "content": response_content})

        # 7. 更新状态计数器
        self._update_counters(context, intent)

        # 8. 返回响应
        return AgentResponse(
            content=response_content,
            current_state=context.current_state.value,
            intent_detected=intent,
            rag_used=requires_rag and rag_results is not None,
            state_changed=state_changed,
            metadata={
                "session_id": session_id,
                "turn_number": len(context.history) // 2,
                "discovery_questions_asked": context.discovery_questions_asked,
                "pitch_attempts": context.pitch_attempts,
                "objections_raised": len(context.objections_raised),
                "closing_attempts": context.closing_attempts
            }
        )

    def _update_state_by_intent(
        self,
        context: ConversationContext,
        intent: str,
        message: str
    ) -> bool:
        """根据意图更新状态"""
        state_changed = False

        # Opening -> Discovery
        if context.current_state == SalesState.OPENING and intent != UserIntent.SOCIAL.value:
            success, _ = self.fsm.transition_to(
                context,
                TransitionTrigger.RAPPORT_ESTABLISHED,
                reason="客户开始交流，破冰成功"
            )
            state_changed = success

        # Discovery -> Pitch
        elif context.current_state == SalesState.DISCOVERY:
            if intent == UserIntent.BUYING_SIGNAL.value:
                success, _ = self.fsm.transition_to(
                    context,
                    TransitionTrigger.BUYING_SIGNAL,
                    reason="检测到购买信号"
                )
                state_changed = success
            elif context.discovery_questions_asked >= 3:
                success, _ = self.fsm.transition_to(
                    context,
                    TransitionTrigger.NEEDS_IDENTIFIED,
                    reason="已收集足够信息"
                )
                state_changed = success

        # Pitch -> Objection
        elif context.current_state == SalesState.PITCH and intent == UserIntent.OBJECTION.value:
            context.objections_raised.append(message[:50])  # 记录异议
            success, _ = self.fsm.transition_to(
                context,
                TransitionTrigger.OBJECTION_RAISED,
                reason="客户提出异议"
            )
            state_changed = success

        # Objection -> Pitch
        elif context.current_state == SalesState.OBJECTION and intent != UserIntent.OBJECTION.value:
            context.objections_resolved.append(context.objections_raised[-1] if context.objections_raised else "")
            success, _ = self.fsm.transition_to(
                context,
                TransitionTrigger.OBJECTION_RESOLVED,
                reason="异议已处理"
            )
            state_changed = success

        # Pitch -> Closing
        elif context.current_state == SalesState.PITCH and intent == UserIntent.BUYING_SIGNAL.value:
            success, _ = self.fsm.transition_to(
                context,
                TransitionTrigger.INTEREST_CONFIRMED,
                reason="客户表达兴趣"
            )
            state_changed = success

        # Closing -> Completed
        elif context.current_state == SalesState.CLOSING and intent == UserIntent.BUYING_SIGNAL.value:
            success, _ = self.fsm.transition_to(
                context,
                TransitionTrigger.COMMITMENT_MADE,
                reason="客户做出承诺"
            )
            state_changed = success

        return state_changed

    def _generate_system_prompt(
        self,
        context: ConversationContext,
        rag_results: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成 System Prompt"""
        current_state = context.current_state

        # 获取基础 Prompt
        if current_state == SalesState.OPENING:
            base_prompt = self.prompt_manager.get_opening_prompt({})

        elif current_state == SalesState.DISCOVERY:
            base_prompt = self.prompt_manager.get_discovery_prompt(
                {},
                questions_asked=context.discovery_questions_asked,
                required_questions=3
            )

        elif current_state == SalesState.PITCH:
            product_info = ""
            if rag_results and rag_results.get("found"):
                data = rag_results.get("data", [])
                product_info = "\n".join([d.get("text", "") for d in data[:3]])

            base_prompt = self.prompt_manager.get_pitch_prompt(
                {},
                customer_needs=context.customer_needs,
                product_info=product_info
            )

        elif current_state == SalesState.OBJECTION:
            objection = context.objections_raised[-1] if context.objections_raised else ""
            base_prompt = self.prompt_manager.get_objection_prompt({}, objection=objection)

        elif current_state == SalesState.CLOSING:
            base_prompt = self.prompt_manager.get_closing_prompt(
                {},
                closing_attempts=context.closing_attempts
            )

        else:
            base_prompt = "你是一位专业的销售顾问，请自然地与客户对话。"

        return base_prompt

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        context: ConversationContext
    ) -> str:
        """调用 LLM 生成响应"""
        # TODO: 集成 ModelGateway
        # 这里需要调用 Phase 4 的 ModelGateway
        logger.warning("LLM call not implemented, using fallback")
        return self._generate_fallback_response(context, UserIntent.UNKNOWN.value)

    def _generate_fallback_response(self, context: ConversationContext, intent: str) -> str:
        """生成后备响应（测试模式）"""
        state = context.current_state

        if state == SalesState.OPENING:
            return "您好！我是XX银行的销售顾问，很高兴为您服务。请问您对信用卡有什么需求吗？"

        elif state == SalesState.DISCOVERY:
            questions_left = 3 - context.discovery_questions_asked
            if questions_left > 0:
                return f"您目前使用信用卡的主要场景是什么？（还需要{questions_left}个问题）"
            else:
                return "根据您的需求，我推荐我们的白金卡..."

        elif state == SalesState.PITCH:
            return "我们的白金卡最高额度可达50万，比市面上普通信用卡高出5倍，这意味着您在大额消费时不用担心额度不够。"

        elif state == SalesState.OBJECTION:
            return "我理解您的顾虑。实际上，我们的年费是可以通过刷卡次数免除的，首年免年费，次年刷满6笔即可免年费。"

        elif state == SalesState.CLOSING:
            return "那我现在帮您办理，需要您提供一下身份证信息和联系方式。"

        else:
            return "请问还有什么我可以帮您的吗？"

    def _update_counters(self, context: ConversationContext, intent: str):
        """更新状态计数器"""
        if context.current_state == SalesState.DISCOVERY:
            if intent == UserIntent.INFORMATIONAL.value:
                context.discovery_questions_asked += 1

        elif context.current_state == SalesState.PITCH:
            context.pitch_attempts += 1

        elif context.current_state == SalesState.OBJECTION:
            context.objection_handling_attempts += 1

        elif context.current_state == SalesState.CLOSING:
            context.closing_attempts += 1


# ============================================================================
# 测试和演示
# ============================================================================

async def demo_single_sales_agent():
    """演示完整的销售对话流程"""
    print("=" * 80)
    print("Phase 3B Week 5 Day 7: Single Sales Agent Demo")
    print("=" * 80)

    # 创建 Agent（测试模式，不使用真实 LLM）
    agent = SingleSalesAgent(knowledge_interface=None, model_gateway=None)

    session_id = "demo-session-001"

    # 模拟完整对话流程
    conversation = [
        ("您好", "Opening"),
        ("我想了解一下信用卡", "Discovery"),
        ("我主要用于商务出差", "Discovery"),
        ("现在的卡额度不够用", "Discovery"),
        ("年费多少钱？", "Pitch"),
        ("太贵了吧", "Objection"),
        ("那还可以，我要办理", "Closing"),
        ("好的，开始办理吧", "Completed")
    ]

    print("\n[Simulating Sales Conversation]")
    print("-" * 80)

    for i, (message, expected_stage) in enumerate(conversation, 1):
        print(f"\n[Turn {i}] Customer: {message}")
        print(f"Expected Stage: {expected_stage}")

        response = await agent.process_message(session_id, message)

        print(f"Agent State: {response.current_state}")
        print(f"Intent Detected: {response.intent_detected}")
        print(f"RAG Used: {response.rag_used}")
        print(f"State Changed: {response.state_changed}")
        print(f"Agent Response: {response.content}")
        print(f"Metadata: {response.metadata}")

    # 最终总结
    print("\n" + "=" * 80)
    print("Conversation Summary")
    print("=" * 80)

    context = agent.sessions[session_id]
    summary = context.to_dict()

    print(f"\nFinal State: {summary['current_state']}")
    print(f"Total Turns: {len(summary['transitions'])}")
    print(f"Discovery Questions: {summary['discovery_questions_asked']}")
    print(f"Pitch Attempts: {summary['pitch_attempts']}")
    print(f"Objections Raised: {len(summary['objections_raised'])}")
    print(f"Closing Attempts: {summary['closing_attempts']}")

    print("\n[OK] Demo completed successfully!")


if __name__ == "__main__":
    import asyncio

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行演示
    asyncio.run(demo_single_sales_agent())
