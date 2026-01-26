"""
State Recovery Service - 状态恢复服务
提供状态恢复和会话重建功能
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from app.services.state_snapshot import StateSnapshot, state_snapshot_service
from app.services.orchestrator import SessionOrchestrator, V3Orchestrator
from app.services.logging_service import structured_logger, metrics_collector
from app.schemas.fsm import FSMState, SalesStage
from app.models.config_models import CustomerPersona, ScenarioConfig

logger = logging.getLogger(__name__)


class StateRecoveryService:
    """状态恢复服务"""

    def __init__(self):
        self.orchestrator_cache = {}

    async def initialize(self):
        """初始化服务"""
        await state_snapshot_service.initialize()
        logger.info("StateRecoveryService initialized")

    async def recover_session_state(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """恢复会话状态"""
        start_time = asyncio.get_event_loop().time()

        try:
            # 获取状态快照
            snapshot = await state_snapshot_service.get_snapshot(session_id)

            if not snapshot:
                structured_logger.log_info(
                    "No snapshot available for session recovery", extra={"session_id": session_id, "user_id": user_id}
                )
                return None

            # 验证用户权限
            if snapshot.user_id != user_id:
                structured_logger.log_warning(
                    "Unauthorized snapshot access attempt",
                    extra={"session_id": session_id, "snapshot_user_id": snapshot.user_id, "request_user_id": user_id},
                )
                return None

            # 重建编排器状态
            orchestrator = await self._rebuild_orchestrator(snapshot)

            if not orchestrator:
                structured_logger.log_error(
                    Exception("Failed to rebuild orchestrator"),
                    extra={"session_id": session_id, "agent_type": snapshot.agent_type},
                )
                return None

            # 恢复执行状态
            await self._restore_execution_state(orchestrator, snapshot)

            recovery_time = asyncio.get_event_loop().time() - start_time
            metrics_collector.record_histogram("session_recovery_time_ms", recovery_time * 1000)
            metrics_collector.increment_counter(
                "session_recoveries_total", 1, {"agent_type": snapshot.agent_type, "stage": snapshot.current_stage}
            )

            structured_logger.log_info(
                "Session state recovered successfully",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "snapshot_id": snapshot.snapshot_id,
                    "agent_type": snapshot.agent_type,
                    "current_stage": snapshot.current_stage,
                    "recovery_time_ms": recovery_time * 1000,
                },
            )

            return {
                "session_id": session_id,
                "user_id": user_id,
                "agent_type": snapshot.agent_type,
                "current_stage": snapshot.current_stage,
                "orchestrator": orchestrator,
                "context": snapshot.context,
                "conversation_history": snapshot.conversation_history,
                "recovered_at": datetime.utcnow().isoformat(),
                "snapshot_created_at": snapshot.created_at.isoformat(),
            }

        except Exception as e:
            structured_logger.log_error(
                e, extra={"session_id": session_id, "user_id": user_id, "operation": "recover_session_state"}
            )
            return None

    async def _rebuild_orchestrator(self, snapshot: StateSnapshot) -> Optional[object]:
        """重建编排器实例"""
        try:
            if snapshot.agent_type == "session_orchestrator":
                # 重建SessionOrchestrator
                orchestrator = SessionOrchestrator()

                # 恢复基本状态
                if hasattr(orchestrator, "initialize_session"):
                    await orchestrator.initialize_session(
                        session_id=snapshot.session_id,
                        user_id=snapshot.user_id,
                        scenario=ScenarioConfig(
                            scenario_type="recovered",
                            customer_persona=CustomerPersona(name="Recovered User", industry="Unknown", role="Unknown"),
                        ),
                    )

                return orchestrator

            elif snapshot.agent_type == "v3_orchestrator":
                # 重建V3Orchestrator
                orchestrator = V3Orchestrator()

                # 恢复V3特定状态
                if hasattr(orchestrator, "initialize"):
                    await orchestrator.initialize()

                return orchestrator

            else:
                logger.error(f"Unknown orchestrator type: {snapshot.agent_type}")
                return None

        except Exception as e:
            structured_logger.log_error(
                e,
                extra={
                    "snapshot_id": snapshot.snapshot_id,
                    "agent_type": snapshot.agent_type,
                    "operation": "_rebuild_orchestrator",
                },
            )
            return None

    async def _restore_execution_state(self, orchestrator, snapshot: StateSnapshot):
        """恢复执行状态"""
        try:
            # 恢复上下文
            if hasattr(orchestrator, "context"):
                orchestrator.context.update(snapshot.context)

            # 恢复记忆
            if hasattr(orchestrator, "memory"):
                orchestrator.memory.update(snapshot.memory)

            # 恢复对话历史
            if hasattr(orchestrator, "conversation_history"):
                orchestrator.conversation_history = snapshot.conversation_history

            # 恢复执行状态
            if hasattr(orchestrator, "execution_state"):
                orchestrator.execution_state.update(snapshot.execution_state)

            # 恢复FSM状态（如果有）
            if hasattr(orchestrator, "fsm_engine") and snapshot.current_stage:
                try:
                    stage = SalesStage(snapshot.current_stage)
                    if hasattr(orchestrator.fsm_engine, "current_state"):
                        orchestrator.fsm_engine.current_state = FSMState(stage=stage)
                except ValueError:
                    logger.warning(f"Invalid stage in snapshot: {snapshot.current_stage}")

            structured_logger.log_info(
                "Execution state restored successfully",
                extra={
                    "snapshot_id": snapshot.snapshot_id,
                    "agent_type": snapshot.agent_type,
                    "context_keys": list(snapshot.context.keys()),
                    "memory_keys": list(snapshot.memory.keys()),
                },
            )

        except Exception as e:
            structured_logger.log_error(
                e,
                extra={
                    "snapshot_id": snapshot.snapshot_id,
                    "agent_type": snapshot.agent_type,
                    "operation": "_restore_execution_state",
                },
            )
            raise

    async def create_recovery_checkpoint(
        self, session_id: str, user_id: str, agent_type: str, orchestrator: object
    ) -> Optional[str]:
        """创建恢复检查点"""
        try:
            # 提取状态信息
            context = getattr(orchestrator, "context", {})
            memory = getattr(orchestrator, "memory", {})
            conversation_history = getattr(orchestrator, "conversation_history", [])
            execution_state = getattr(orchestrator, "execution_state", {})

            # 获取当前阶段
            current_stage = "unknown"
            if hasattr(orchestrator, "fsm_engine") and hasattr(orchestrator.fsm_engine, "current_state"):
                current_stage = orchestrator.fsm_engine.current_state.stage.value
            elif hasattr(orchestrator, "current_stage"):
                current_stage = orchestrator.current_stage

            # 创建快照
            snapshot_id = await state_snapshot_service.create_snapshot(
                session_id=session_id,
                user_id=user_id,
                agent_type=agent_type,
                current_stage=current_stage,
                context=context,
                memory=memory,
                conversation_history=conversation_history,
                execution_state=execution_state,
                ttl_hours=24,  # 24小时过期
            )

            metrics_collector.increment_counter(
                "recovery_checkpoints_created_total", 1, {"agent_type": agent_type, "stage": current_stage}
            )

            structured_logger.log_info(
                "Recovery checkpoint created successfully",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "snapshot_id": snapshot_id,
                    "agent_type": agent_type,
                    "current_stage": current_stage,
                },
            )

            return snapshot_id

        except Exception as e:
            structured_logger.log_error(
                e,
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "agent_type": agent_type,
                    "operation": "create_recovery_checkpoint",
                },
            )
            return None

    async def list_recoverable_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """列出可恢复的会话"""
        try:
            snapshots = await state_snapshot_service.get_session_snapshots(user_id)

            recoverable_sessions = []
            for snapshot in snapshots:
                session_info = {
                    "session_id": snapshot.session_id,
                    "agent_type": snapshot.agent_type,
                    "current_stage": snapshot.current_stage,
                    "created_at": snapshot.created_at.isoformat(),
                    "expires_at": snapshot.expires_at.isoformat(),
                    "conversation_length": len(snapshot.conversation_history),
                    "snapshot_id": snapshot.snapshot_id,
                }
                recoverable_sessions.append(session_info)

            metrics_collector.record_histogram("recoverable_sessions_count", len(recoverable_sessions))

            structured_logger.log_info(
                "Listed recoverable sessions", extra={"user_id": user_id, "session_count": len(recoverable_sessions)}
            )

            return recoverable_sessions

        except Exception as e:
            structured_logger.log_error(e, extra={"user_id": user_id, "operation": "list_recoverable_sessions"})
            return []

    async def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        try:
            cleaned_count = await state_snapshot_service.cleanup_expired_snapshots()

            metrics_collector.increment_counter("expired_sessions_cleanup_total", 1, {"cleaned_count": cleaned_count})

            structured_logger.log_info("Expired sessions cleanup completed", extra={"cleaned_count": cleaned_count})

            return cleaned_count

        except Exception as e:
            structured_logger.log_error(e, extra={"operation": "cleanup_expired_sessions"})
            return 0


# 全局实例
state_recovery_service = StateRecoveryService()
