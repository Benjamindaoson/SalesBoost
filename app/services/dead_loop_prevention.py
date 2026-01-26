"""
Agent Dead Loop Prevention System - Agent死循环防护系统
防止多智能体系统陷入无限循环，实现执行深度和时间限制
"""

import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from enum import Enum
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class LoopDetectionLevel(Enum):
    """循环检测级别"""

    SAFE = "safe"
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCKED = "blocked"


@dataclass
class ExecutionState:
    """执行状态跟踪"""

    session_id: str
    execution_id: str
    current_depth: int = 0
    max_depth_limit: int = 50
    start_time: float = 0.0
    max_time_limit: float = 300.0  # 5分钟
    call_stack: List[str] = None
    state_history: List[Dict[str, Any]] = None
    loop_patterns: Set[str] = None
    intervention_triggered: bool = False

    def __post_init__(self):
        if self.call_stack is None:
            self.call_stack = []
        if self.state_history is None:
            self.state_history = []
        if self.loop_patterns is None:
            self.loop_patterns = set()


class DeadLoopDetector:
    """死循环检测器"""

    def __init__(self):
        self.active_executions: Dict[str, ExecutionState] = {}
        self.loop_threshold = 3  # 重复3次状态视为循环
        self.state_similarity_threshold = 0.9  # 状态相似度阈值

    async def start_execution(self, session_id: str, max_depth: int = 50, max_time_seconds: float = 300.0) -> str:
        """开始执行跟踪"""
        execution_id = str(uuid.uuid4())

        execution_state = ExecutionState(
            session_id=session_id,
            execution_id=execution_id,
            max_depth_limit=max_depth,
            max_time_limit=max_time_seconds,
            start_time=time.time(),
        )

        self.active_executions[session_id] = execution_state

        logger.info(f"Started execution tracking: {execution_id} for session {session_id}")
        return execution_id

    async def check_execution_limits(self, session_id: str) -> LoopDetectionLevel:
        """检查执行限制"""
        if session_id not in self.active_executions:
            return LoopDetectionLevel.SAFE

        state = self.active_executions[session_id]
        current_time = time.time()

        # 检查执行深度
        if state.current_depth >= state.max_depth_limit:
            logger.warning(f"Execution depth limit exceeded: {state.current_depth} >= {state.max_depth_limit}")
            return LoopDetectionLevel.BLOCKED

        # 检查执行时间
        elapsed_time = current_time - state.start_time
        if elapsed_time >= state.max_time_limit:
            logger.warning(f"Execution time limit exceeded: {elapsed_time:.1f}s >= {state.max_time_limit}s")
            return LoopDetectionLevel.BLOCKED

        # 检查重复状态模式
        loop_detected = self._detect_loop_patterns(state)
        if loop_detected == LoopDetectionLevel.CRITICAL:
            return LoopDetectionLevel.CRITICAL
        elif loop_detected == LoopDetectionLevel.WARNING:
            return LoopDetectionLevel.WARNING

        return LoopDetectionLevel.SAFE

    async def increment_depth(self, session_id: str, step_name: str = "unknown") -> bool:
        """增加执行深度"""
        if session_id not in self.active_executions:
            return False

        state = self.active_executions[session_id]
        state.current_depth += 1
        state.call_stack.append(step_name)

        # 检查深度限制
        if state.current_depth >= state.max_depth_limit:
            logger.warning(f"Depth limit reached: {state.current_depth}/{state.max_depth_limit}")
            return False

        logger.debug(f"Execution depth incremented: {state.current_depth}/{state.max_depth_limit}")
        return True

    async def record_state(self, session_id: str, state_data: Dict[str, Any]) -> LoopDetectionLevel:
        """记录执行状态"""
        if session_id not in self.active_executions:
            return LoopDetectionLevel.SAFE

        execution_state = self.active_executions[session_id]
        execution_state.state_history.append(
            {"timestamp": time.time(), "depth": execution_state.current_depth, "state": state_data.copy()}
        )

        # 限制历史记录数量
        if len(execution_state.state_history) > 100:
            execution_state.state_history = execution_state.state_history[-50:]

        return await self.check_execution_limits(session_id)

    async def end_execution(self, session_id: str) -> Dict[str, Any]:
        """结束执行跟踪"""
        if session_id not in self.active_executions:
            return {"error": "No active execution found"}

        state = self.active_executions[session_id]
        end_time = time.time()
        execution_time = end_time - state.start_time

        summary = {
            "execution_id": state.execution_id,
            "session_id": session_id,
            "total_depth": state.current_depth,
            "execution_time_seconds": execution_time,
            "max_depth_reached": state.current_depth >= state.max_depth_limit,
            "time_limit_reached": execution_time >= state.max_time_limit,
            "loop_detected": len(state.loop_patterns) > 0,
            "call_stack": state.call_stack.copy(),
            "intervention_triggered": state.intervention_triggered,
        }

        del self.active_executions[session_id]

        logger.info(f"Execution completed: {summary}")
        return summary

    def _detect_loop_patterns(self, state: ExecutionState) -> LoopDetectionLevel:
        """检测循环模式"""
        if len(state.state_history) < 3:
            return LoopDetectionLevel.SAFE

        # 简单的状态重复检测
        recent_states = state.state_history[-10:]  # 检查最近10个状态

        state_signatures = []
        for state_record in recent_states:
            # 创建状态签名（简化版本）
            signature = self._create_state_signature(state_record["state"])
            state_signatures.append(signature)

        # 检查重复模式
        signature_counts = defaultdict(int)
        for signature in state_signatures:
            signature_counts[signature] += 1

        # 找出频繁重复的状态
        max_count = max(signature_counts.values()) if signature_counts else 0
        most_frequent_signatures = [sig for sig, count in signature_counts.items() if count == max_count]

        if max_count >= self.loop_threshold:
            for signature in most_frequent_signatures:
                if signature not in state.loop_patterns:
                    state.loop_patterns.add(signature)
                    logger.warning(f"Potential loop pattern detected: {signature} (count: {max_count})")

            if max_count >= 5:
                return LoopDetectionLevel.CRITICAL
            elif max_count >= 3:
                return LoopDetectionLevel.WARNING

        return LoopDetectionLevel.SAFE

    def _create_state_signature(self, state_data: Dict[str, Any]) -> str:
        """创建状态签名"""
        # 提取关键状态信息创建签名
        key_fields = ["agent_type", "current_stage", "last_action", "next_action", "decision_point"]

        signature_parts = []
        for field in key_fields:
            if field in state_data:
                value = state_data[field]
                # 简化复杂对象
                if isinstance(value, (dict, list)):
                    signature_parts.append(f"{field}:{type(value).__name__}")
                else:
                    signature_parts.append(f"{field}:{str(value)[:50]}")

        return "|".join(signature_parts)

    def get_execution_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        if session_id not in self.active_executions:
            return None

        state = self.active_executions[session_id]
        current_time = time.time()
        elapsed_time = current_time - state.start_time

        return {
            "session_id": session_id,
            "execution_id": state.execution_id,
            "current_depth": state.current_depth,
            "max_depth_limit": state.max_depth_limit,
            "elapsed_time_seconds": elapsed_time,
            "max_time_limit": state.max_time_limit,
            "depth_percentage": (state.current_depth / state.max_depth_limit) * 100,
            "time_percentage": (elapsed_time / state.max_time_limit) * 100,
            "loop_patterns_count": len(state.loop_patterns),
            "call_stack_length": len(state.call_stack),
            "risk_level": self._calculate_risk_level(state, elapsed_time),
        }

    def _calculate_risk_level(self, state: ExecutionState, elapsed_time: float) -> str:
        """计算风险级别"""
        depth_ratio = state.current_depth / state.max_depth_limit
        time_ratio = elapsed_time / state.max_time_limit
        loop_ratio = len(state.loop_patterns) / 5.0  # 假设5个模式为高风险

        overall_risk = (depth_ratio + time_ratio + loop_ratio) / 3

        if overall_risk >= 0.8:
            return "HIGH"
        elif overall_risk >= 0.6:
            return "MEDIUM"
        elif overall_risk >= 0.3:
            return "LOW"
        else:
            return "SAFE"


class LoopInterventionHandler:
    """循环干预处理器"""

    def __init__(self):
        self.intervention_strategies = {
            LoopDetectionLevel.WARNING: self._handle_warning,
            LoopDetectionLevel.CRITICAL: self._handle_critical,
            LoopDetectionLevel.BLOCKED: self._handle_blocked,
        }

    async def handle_intervention(
        self, session_id: str, detection_level: LoopDetectionLevel, execution_state: ExecutionState
    ) -> Dict[str, Any]:
        """处理循环干预"""
        handler = self.intervention_strategies.get(detection_level)
        if handler:
            return await handler(session_id, execution_state)
        else:
            return {"status": "no_intervention", "reason": "no_handler"}

    async def _handle_warning(self, session_id: str, state: ExecutionState) -> Dict[str, Any]:
        """处理警告级别的循环"""
        logger.warning(f"Loop warning for session {session_id}, attempting gentle intervention")

        return {
            "status": "warning_intervention",
            "action": "log_warning",
            "suggestion": "Consider adding state randomness or reducing complexity",
            "execution_depth": state.current_depth,
            "loop_patterns": list(state.loop_patterns),
        }

    async def _handle_critical(self, session_id: str, state: ExecutionState) -> Dict[str, Any]:
        """处理严重级别的循环"""
        logger.error(f"Critical loop detected for session {session_id}, forcing intervention")

        return {
            "status": "critical_intervention",
            "action": "force_termination",
            "reason": "critical_loop_detected",
            "execution_depth": state.current_depth,
            "loop_patterns": list(state.loop_patterns),
            "restart_recommended": True,
        }

    async def _handle_blocked(self, session_id: str, state: ExecutionState) -> Dict[str, Any]:
        """处理阻断级别的循环"""
        logger.error(f"Execution blocked for session {session_id}, limits exceeded")

        return {
            "status": "blocked_intervention",
            "action": "emergency_stop",
            "reason": "execution_limits_exceeded",
            "execution_depth": state.current_depth,
            "elapsed_time": time.time() - state.start_time,
            "manual_intervention_required": True,
        }


# 全局实例
dead_loop_detector = DeadLoopDetector()
loop_intervention_handler = LoopInterventionHandler()
