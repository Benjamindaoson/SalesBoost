"""
Sales Conversation Finite State Machine (FSM)

Phase 3B Week 5 Day 1-2 交付物

集成到 SalesBoost agent 架构的销售状态机
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class SalesState(str, Enum):
    """销售对话状态枚举"""
    OPENING = "opening"          # 开场破冰
    DISCOVERY = "discovery"      # 需求挖掘
    PITCH = "pitch"              # 产品推介
    OBJECTION = "objection"      # 异议处理
    CLOSING = "closing"          # 缔结成交
    COMPLETED = "completed"      # 对话完成
    FAILED = "failed"            # 对话失败


class TransitionTrigger(str, Enum):
    """状态转换触发器"""
    # Opening -> Discovery
    RAPPORT_ESTABLISHED = "rapport_established"

    # Discovery -> Pitch
    NEEDS_IDENTIFIED = "needs_identified"
    BUYING_SIGNAL = "buying_signal"

    # Pitch -> Objection
    OBJECTION_RAISED = "objection_raised"

    # Objection -> Pitch
    OBJECTION_RESOLVED = "objection_resolved"

    # Pitch -> Closing
    INTEREST_CONFIRMED = "interest_confirmed"

    # Closing -> Completed
    COMMITMENT_MADE = "commitment_made"

    # Any -> Failed
    HARD_REJECTION = "hard_rejection"
    CONVERSATION_ENDED = "conversation_ended"

    # Fallback
    MANUAL_OVERRIDE = "manual_override"


@dataclass
class StateTransition:
    """状态转换记录"""
    from_state: SalesState
    to_state: SalesState
    trigger: TransitionTrigger
    timestamp: datetime
    reason: str
    confidence: float = 1.0


@dataclass
class ConversationContext:
    """对话上下文"""
    session_id: str
    current_state: SalesState
    history: List[Dict[str, str]] = field(default_factory=list)
    transitions: List[StateTransition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Discovery 阶段收集的信息
    customer_needs: List[str] = field(default_factory=list)
    pain_points: List[str] = field(default_factory=list)
    budget_range: Optional[str] = None
    decision_timeline: Optional[str] = None

    # Objection 阶段记录
    objections_raised: List[str] = field(default_factory=list)
    objections_resolved: List[str] = field(default_factory=list)

    # 状态计数器
    discovery_questions_asked: int = 0
    pitch_attempts: int = 0
    objection_handling_attempts: int = 0
    closing_attempts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "current_state": self.current_state.value,
            "history_length": len(self.history),
            "transitions": [
                {
                    "from": t.from_state.value,
                    "to": t.to_state.value,
                    "trigger": t.trigger.value,
                    "timestamp": t.timestamp.isoformat(),
                    "reason": t.reason,
                    "confidence": t.confidence
                }
                for t in self.transitions
            ],
            "customer_needs": self.customer_needs,
            "pain_points": self.pain_points,
            "budget_range": self.budget_range,
            "decision_timeline": self.decision_timeline,
            "objections_raised": self.objections_raised,
            "objections_resolved": self.objections_resolved,
            "discovery_questions_asked": self.discovery_questions_asked,
            "pitch_attempts": self.pitch_attempts,
            "objection_handling_attempts": self.objection_handling_attempts,
            "closing_attempts": self.closing_attempts,
            "metadata": self.metadata
        }


class StateTransitionRule:
    """状态转换规则"""

    def __init__(
        self,
        from_state: SalesState,
        to_state: SalesState,
        trigger: TransitionTrigger,
        condition: Optional[callable] = None,
        priority: int = 0
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.trigger = trigger
        self.condition = condition
        self.priority = priority

    def can_transition(self, context: ConversationContext) -> Tuple[bool, str]:
        """检查是否可以执行转换"""
        if context.current_state != self.from_state:
            return False, f"Current state {context.current_state} does not match {self.from_state}"

        if self.condition:
            try:
                result = self.condition(context)
                if not result:
                    return False, "Custom condition not met"
            except Exception as e:
                logger.error(f"Condition check failed: {e}")
                return False, f"Condition check error: {e}"

        return True, "Transition allowed"


class SalesConversationFSM:
    """
    销售对话有限状态机

    核心功能：
    1. 状态管理：跟踪当前对话状态
    2. 状态转换：根据触发器和规则进行状态转换
    3. 上下文维护：记录对话历史和关键信息
    4. 转换验证：确保状态转换的合法性
    """

    def __init__(self):
        self.transition_rules: List[StateTransitionRule] = []
        self._initialize_rules()

    def _initialize_rules(self):
        """初始化状态转换规则"""

        # Opening -> Discovery
        self.add_rule(
            from_state=SalesState.OPENING,
            to_state=SalesState.DISCOVERY,
            trigger=TransitionTrigger.RAPPORT_ESTABLISHED,
            condition=None,
            priority=10
        )

        # Discovery -> Pitch
        self.add_rule(
            from_state=SalesState.DISCOVERY,
            to_state=SalesState.PITCH,
            trigger=TransitionTrigger.NEEDS_IDENTIFIED,
            condition=lambda ctx: ctx.discovery_questions_asked >= 3,
            priority=10
        )

        self.add_rule(
            from_state=SalesState.DISCOVERY,
            to_state=SalesState.PITCH,
            trigger=TransitionTrigger.BUYING_SIGNAL,
            condition=None,
            priority=15
        )

        # Pitch -> Objection
        self.add_rule(
            from_state=SalesState.PITCH,
            to_state=SalesState.OBJECTION,
            trigger=TransitionTrigger.OBJECTION_RAISED,
            condition=None,
            priority=10
        )

        # Objection -> Pitch
        self.add_rule(
            from_state=SalesState.OBJECTION,
            to_state=SalesState.PITCH,
            trigger=TransitionTrigger.OBJECTION_RESOLVED,
            condition=None,
            priority=10
        )

        # Pitch -> Closing
        self.add_rule(
            from_state=SalesState.PITCH,
            to_state=SalesState.CLOSING,
            trigger=TransitionTrigger.INTEREST_CONFIRMED,
            condition=lambda ctx: ctx.pitch_attempts >= 1,
            priority=10
        )

        # Closing -> Completed
        self.add_rule(
            from_state=SalesState.CLOSING,
            to_state=SalesState.COMPLETED,
            trigger=TransitionTrigger.COMMITMENT_MADE,
            condition=None,
            priority=10
        )

        # Any -> Failed
        for state in [SalesState.OPENING, SalesState.DISCOVERY, SalesState.PITCH,
                      SalesState.OBJECTION, SalesState.CLOSING]:
            self.add_rule(
                from_state=state,
                to_state=SalesState.FAILED,
                trigger=TransitionTrigger.HARD_REJECTION,
                condition=None,
                priority=20
            )

        logger.info(f"Initialized {len(self.transition_rules)} transition rules")

    def add_rule(
        self,
        from_state: SalesState,
        to_state: SalesState,
        trigger: TransitionTrigger,
        condition: Optional[callable] = None,
        priority: int = 0
    ):
        """添加状态转换规则"""
        rule = StateTransitionRule(from_state, to_state, trigger, condition, priority)
        self.transition_rules.append(rule)
        self.transition_rules.sort(key=lambda r: r.priority, reverse=True)

    def create_context(self, session_id: str) -> ConversationContext:
        """创建新的对话上下文"""
        return ConversationContext(
            session_id=session_id,
            current_state=SalesState.OPENING,
            metadata={"created_at": datetime.now().isoformat()}
        )

    def transition_to(
        self,
        context: ConversationContext,
        trigger: TransitionTrigger,
        reason: str = "",
        confidence: float = 1.0
    ) -> Tuple[bool, str]:
        """尝试执行状态转换"""
        matching_rules = [
            rule for rule in self.transition_rules
            if rule.trigger == trigger and rule.from_state == context.current_state
        ]

        if not matching_rules:
            msg = f"No transition rule found for {context.current_state} with trigger {trigger}"
            logger.warning(msg)
            return False, msg

        for rule in matching_rules:
            can_transition, check_reason = rule.can_transition(context)

            if can_transition:
                old_state = context.current_state
                new_state = rule.to_state

                transition = StateTransition(
                    from_state=old_state,
                    to_state=new_state,
                    trigger=trigger,
                    timestamp=datetime.now(),
                    reason=reason or check_reason,
                    confidence=confidence
                )

                context.current_state = new_state
                context.transitions.append(transition)

                logger.info(
                    f"State transition: {old_state.value} -> {new_state.value} "
                    f"(trigger: {trigger.value}, confidence: {confidence:.2f})"
                )

                return True, f"Transitioned to {new_state.value}"

        msg = f"Transition conditions not met for {trigger.value}"
        logger.warning(msg)
        return False, msg

    def get_allowed_transitions(self, context: ConversationContext) -> List[TransitionTrigger]:
        """获取当前状态允许的转换触发器"""
        allowed = []
        for rule in self.transition_rules:
            if rule.from_state == context.current_state:
                can_transition, _ = rule.can_transition(context)
                if can_transition:
                    allowed.append(rule.trigger)
        return list(set(allowed))

    def get_state_requirements(self, state: SalesState) -> Dict[str, Any]:
        """获取进入某个状态的要求"""
        requirements = {
            SalesState.OPENING: {
                "goal": "建立信任和融洽关系",
                "min_turns": 1,
                "key_actions": ["自我介绍", "破冰", "建立共鸣"],
                "exit_condition": "客户愿意继续对话"
            },
            SalesState.DISCOVERY: {
                "goal": "挖掘客户需求和痛点",
                "min_turns": 3,
                "key_actions": ["SPIN提问", "倾听", "确认理解"],
                "exit_condition": "识别出至少1个明确需求",
                "required_questions": 3
            },
            SalesState.PITCH: {
                "goal": "呈现产品方案和价值",
                "min_turns": 1,
                "key_actions": ["FAB呈现", "案例分享", "价值锚定"],
                "exit_condition": "客户表达兴趣或提出异议"
            },
            SalesState.OBJECTION: {
                "goal": "处理客户异议和顾虑",
                "min_turns": 1,
                "key_actions": ["倾听异议", "共情", "提供解决方案"],
                "exit_condition": "异议得到解决或缓解"
            },
            SalesState.CLOSING: {
                "goal": "推进下一步行动",
                "min_turns": 1,
                "key_actions": ["试探成交", "提供选择", "确认承诺"],
                "exit_condition": "客户做出承诺或明确拒绝"
            }
        }
        return requirements.get(state, {})

    def analyze_conversation_progress(self, context: ConversationContext) -> Dict[str, Any]:
        """分析对话进展"""
        current_state = context.current_state
        requirements = self.get_state_requirements(current_state)

        analysis = {
            "current_state": current_state.value,
            "state_goal": requirements.get("goal", ""),
            "progress": {},
            "recommendations": [],
            "can_advance": False
        }

        # Discovery 阶段分析
        if current_state == SalesState.DISCOVERY:
            required_questions = requirements.get("required_questions", 3)
            asked = context.discovery_questions_asked

            analysis["progress"] = {
                "questions_asked": asked,
                "questions_required": required_questions,
                "completion": min(100, int(asked / required_questions * 100))
            }

            if asked < required_questions:
                analysis["recommendations"].append(
                    f"继续提问，还需要 {required_questions - asked} 个问题"
                )
            else:
                analysis["can_advance"] = True
                analysis["recommendations"].append("已收集足够信息，可以进入推介阶段")

        # Pitch 阶段分析
        elif current_state == SalesState.PITCH:
            analysis["progress"] = {
                "pitch_attempts": context.pitch_attempts,
                "objections_raised": len(context.objections_raised)
            }

            if context.pitch_attempts == 0:
                analysis["recommendations"].append("开始产品推介，使用FAB法则")
            elif len(context.objections_raised) > 0:
                analysis["recommendations"].append("客户提出异议，准备进入异议处理")
            else:
                analysis["can_advance"] = True
                analysis["recommendations"].append("观察客户反应，寻找成交信号")

        # Objection 阶段分析
        elif current_state == SalesState.OBJECTION:
            unresolved = set(context.objections_raised) - set(context.objections_resolved)

            analysis["progress"] = {
                "objections_raised": len(context.objections_raised),
                "objections_resolved": len(context.objections_resolved),
                "unresolved": len(unresolved)
            }

            if unresolved:
                analysis["recommendations"].append(
                    f"处理未解决的异议: {', '.join(list(unresolved)[:2])}"
                )
            else:
                analysis["can_advance"] = True
                analysis["recommendations"].append("异议已解决，可以继续推介或尝试成交")

        # Closing 阶段分析
        elif current_state == SalesState.CLOSING:
            analysis["progress"] = {
                "closing_attempts": context.closing_attempts
            }

            if context.closing_attempts == 0:
                analysis["recommendations"].append("尝试试探性成交")
            elif context.closing_attempts < 3:
                analysis["recommendations"].append("提供具体的下一步选择")
            else:
                analysis["recommendations"].append("考虑降低承诺门槛或安排后续跟进")

        return analysis
