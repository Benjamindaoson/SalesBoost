"""
Human-in-the-Loop Coordinator
Extends LangGraph coordinator with interrupt mechanism for human review
"""
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END

from app.engine.coordinator.langgraph_coordinator import LangGraphCoordinator
from app.engine.coordinator.state import CoordinatorState
from app.engine.coordinator.trace_utils import build_trace_event
from app.infra.gateway.schemas import AgentType

logger = logging.getLogger(__name__)


class HumanReviewDecision:
    """人工审核决策"""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


class HumanInLoopCoordinator(LangGraphCoordinator):
    """
    支持人机协作的编排器

    Features:
        - 合规门阻塞时触发人工审核
        - 检查点机制支持暂停/恢复
        - WebSocket通知管理员

    Usage:
        coordinator = HumanInLoopCoordinator(...)

        # 执行可能触发中断的对话
        result = await coordinator.execute_turn(...)

        if result.get("requires_human_review"):
            # 等待管理员审核
            decision = await wait_for_admin_decision(session_id)

            # 恢复执行
            final_result = await coordinator.resume_after_review(
                session_id, decision
            )
    """

    def __init__(self, model_gateway, budget_manager, persona,
                 enable_checkpoints: bool = True):
        """
        Args:
            enable_checkpoints: 是否启用检查点（用于暂停/恢复）
        """
        super().__init__(model_gateway, budget_manager, persona)

        self.enable_checkpoints = enable_checkpoints

        # 检查点存储（生产环境应使用Redis/PostgreSQL）
        if enable_checkpoints:
            self.checkpointer = MemorySaver()
            # 重新编译图，启用检查点
            self.app = self.graph.compile(checkpointer=self.checkpointer)

        # 待审核会话队列
        self.pending_reviews: Dict[str, Dict[str, Any]] = {}

        # 审核超时时间（秒）
        self.review_timeout = 300  # 5分钟

    def _build_graph(self) -> StateGraph:
        """重写图构建，添加人工审核节点"""
        workflow = StateGraph(CoordinatorState)

        # 节点
        workflow.add_node("intent", self._intent_node)
        workflow.add_node("tools", self._tools_node)
        workflow.add_node("npc", self._npc_node)
        workflow.add_node("coach", self._coach_node)
        workflow.add_node("compliance_review", self._compliance_review_node)  # 新增
        workflow.add_node("human_review", self._human_review_node)  # 新增

        # 入口
        workflow.set_entry_point("intent")

        # 路由
        workflow.add_conditional_edges(
            "intent",
            self._route_after_intent,
            {"tools": "tools", "npc": "npc"}
        )

        workflow.add_edge("tools", "npc")
        workflow.add_edge("npc", "coach")

        # Coach -> 合规审核（新增）
        workflow.add_edge("coach", "compliance_review")

        # 合规审核 -> 条件路由
        workflow.add_conditional_edges(
            "compliance_review",
            self._route_after_compliance,
            {
                "human_review": "human_review",  # 需要人工审核
                "end": END  # 自动通过
            }
        )

        # 人工审核 -> 结束（审核完成后）
        workflow.add_edge("human_review", END)

        return workflow

    async def _compliance_review_node(self, state: CoordinatorState) -> Dict:
        """????????????"""
        start = time.perf_counter()
        npc_response = state.get("npc_response", "")

        exec_result = await self.tool_executor.execute(
            "compliance_check",
            {
                "text": npc_response,
                "stage": state.get("fsm_state", {}).get("current_stage"),
                "context": {"session_id": state.get("session_id")},
            },
            caller_role=AgentType.COMPLIANCE.value,
            tool_call_id=self._make_tool_call_id("compliance_check", state),
        )
        result = exec_result["result"] if exec_result["ok"] else {"risk_level": "ERROR", "risk_flags": []}
        violations = [flag.get("risk_type") for flag in result.get("risk_flags", [])]
        risk_level = result.get("risk_level", "ERROR")
        risk_score = 0.0
        if risk_level == "WARN":
            risk_score = 0.6
        elif risk_level == "BLOCK":
            risk_score = 0.9

        requires_human_review = False
        severity = "low"
        if risk_score > 0.8:
            requires_human_review = True
            severity = "critical"
        elif risk_score > 0.6:
            requires_human_review = True
            severity = "medium"

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "compliance_result": {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "violations": violations,
                "requires_human_review": requires_human_review,
                "severity": severity
            },
            "tool_outputs": [exec_result],
            "trace_log": [
                build_trace_event(
                    node="compliance_review",
                    status="ok" if not requires_human_review else "warn",
                    source=exec_result.get("audit", {}).get("status"),
                    latency_ms=latency_ms,
                    detail={
                        "risk_score": risk_score,
                        "requires_human_review": requires_human_review,
                        "severity": severity,
                    },
                )
            ],
        }

    async def _human_review_node(self, state: CoordinatorState) -> Dict:
        """???????????"""
        start = time.perf_counter()
        session_id = state["session_id"]

        self.pending_reviews[session_id] = {
            "state": state,
            "timestamp": datetime.utcnow(),
            "status": "pending"
        }

        logger.info(
            f"[HumanReview] Session {session_id} requires human review. "
            f"Risk score: {state['compliance_result']['risk_score']:.2f}"
        )

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "human_review_status": "pending",
            "requires_human_review": True,
            "trace_log": [
                build_trace_event(
                    node="human_review",
                    status="interrupted",
                    latency_ms=latency_ms,
                    detail={"status": "pending"},
                )
            ],
        }

    def _route_after_compliance(self, state: CoordinatorState) -> str:
        """合规审核后的路由决策"""
        compliance_result = state.get("compliance_result", {})

        if compliance_result.get("requires_human_review"):
            return "human_review"
        else:
            return "end"

    async def resume_after_review(
        self,
        session_id: str,
        decision: str,
        modified_content: Optional[str] = None,
        admin_id: str = "system"
    ) -> Dict[str, Any]:
        """
        人工审核后恢复执行

        Args:
            session_id: 会话ID
            decision: 审核决策 (approve/reject/modify)
            modified_content: 修改后的内容（decision=modify时必需）
            admin_id: 审核员ID

        Returns:
            最终执行结果
        """
        if session_id not in self.pending_reviews:
            raise ValueError(f"No pending review for session: {session_id}")

        review_data = self.pending_reviews[session_id]
        state = review_data["state"]

        # 记录审核决策
        logger.info(
            f"[HumanReview] Session {session_id} reviewed by {admin_id}: {decision}"
        )

        # 根据决策更新状态
        if decision == HumanReviewDecision.APPROVE:
            # 批准 -> 使用原始内容
            state["final_npc_reply"] = state["npc_response"]
            state["human_review_result"] = {
                "decision": "approve",
                "reviewer": admin_id,
                "timestamp": datetime.utcnow().isoformat()
            }

        elif decision == HumanReviewDecision.MODIFY:
            # 修改 -> 使用修改后内容
            if not modified_content:
                raise ValueError("modified_content is required when decision=modify")

            state["final_npc_reply"] = modified_content
            state["human_review_result"] = {
                "decision": "modify",
                "reviewer": admin_id,
                "original_content": state["npc_response"],
                "modified_content": modified_content,
                "timestamp": datetime.utcnow().isoformat()
            }

        elif decision == HumanReviewDecision.REJECT:
            # 拒绝 -> 返回默认拒绝消息
            state["final_npc_reply"] = "[此回复因合规问题已被阻止，请重新提问]"
            state["human_review_result"] = {
                "decision": "reject",
                "reviewer": admin_id,
                "rejected_content": state["npc_response"],
                "timestamp": datetime.utcnow().isoformat()
            }

        else:
            raise ValueError(f"Invalid decision: {decision}")

        # 清理待审核队列
        del self.pending_reviews[session_id]

        # 更新状态标记
        state["human_review_status"] = "completed"
        state["requires_human_review"] = False

        return {
            "npc_reply": state["final_npc_reply"],
            "coach_advice": state.get("coach_advice"),
            "human_review_result": state["human_review_result"],
            "trace": state["trace_log"]
        }

    def get_pending_reviews(self) -> Dict[str, Dict]:
        """获取所有待审核会话"""
        return {
            session_id: {
                "risk_score": review["state"]["compliance_result"]["risk_score"],
                "violations": review["state"]["compliance_result"]["violations"],
                "npc_response": review["state"]["npc_response"],
                "timestamp": review["timestamp"].isoformat(),
                "status": review["status"]
            }
            for session_id, review in self.pending_reviews.items()
        }

    async def auto_reject_expired_reviews(self):
        """自动拒绝超时未审核的会话"""
        now = datetime.utcnow()
        expired_sessions = []

        for session_id, review in self.pending_reviews.items():
            elapsed = (now - review["timestamp"]).total_seconds()
            if elapsed > self.review_timeout:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            logger.warning(
                f"[HumanReview] Session {session_id} expired, auto-rejecting"
            )
            await self.resume_after_review(
                session_id,
                decision=HumanReviewDecision.REJECT,
                admin_id="system_auto_reject"
            )
