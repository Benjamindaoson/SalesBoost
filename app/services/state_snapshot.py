"""
State Snapshot Service - 状态快照服务
实现任务中断后的状态恢复机制
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import uuid
import logging

from app.core.database import get_db_session
from app.core.redis import get_redis
from app.services.logging_service import structured_logger, metrics_collector

logger = logging.getLogger(__name__)


@dataclass
class StateSnapshot:
    """状态快照数据结构"""

    snapshot_id: str
    session_id: str
    user_id: str
    agent_type: str
    current_stage: str
    context: Dict[str, Any]
    memory: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    execution_state: Dict[str, Any]
    created_at: datetime
    expires_at: datetime


class StateSnapshotService:
    """状态快照服务"""

    def __init__(self):
        self.redis = None
        self.snapshots_in_memory = {}  # 内存备份

    async def initialize(self):
        """初始化服务"""
        try:
            self.redis = await get_redis()
            logger.info("StateSnapshotService initialized with Redis")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory storage: {e}")

    async def create_snapshot(
        self,
        session_id: str,
        user_id: str,
        agent_type: str,
        current_stage: str,
        context: Dict[str, Any],
        memory: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        execution_state: Dict[str, Any],
        ttl_hours: int = 24,
    ) -> str:
        """创建状态快照"""
        start_time = asyncio.get_event_loop().time()

        try:
            snapshot_id = str(uuid.uuid4())
            now = datetime.utcnow()
            expires_at = now + timedelta(hours=ttl_hours)

            snapshot = StateSnapshot(
                snapshot_id=snapshot_id,
                session_id=session_id,
                user_id=user_id,
                agent_type=agent_type,
                current_stage=current_stage,
                context=context,
                memory=memory,
                conversation_history=conversation_history,
                execution_state=execution_state,
                created_at=now,
                expires_at=expires_at,
            )

            # 序列化快照数据
            snapshot_data = json.dumps(asdict(snapshot), default=str)

            # 保存到Redis
            if self.redis:
                await self.redis.setex(f"snapshot:{session_id}", ttl_hours * 3600, snapshot_data)

            # 内存备份
            self.snapshots_in_memory[session_id] = snapshot

            # 记录指标
            creation_time = asyncio.get_event_loop().time() - start_time
            metrics_collector.record_histogram("snapshot_creation_time_ms", creation_time * 1000)
            metrics_collector.increment_counter(
                "snapshots_created_total", 1, {"agent_type": agent_type, "stage": current_stage}
            )

            structured_logger.log_info(
                "State snapshot created successfully",
                extra={
                    "snapshot_id": snapshot_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "agent_type": agent_type,
                    "current_stage": current_stage,
                    "creation_time_ms": creation_time * 1000,
                },
            )

            return snapshot_id

        except Exception as e:
            structured_logger.log_error(
                e, extra={"session_id": session_id, "user_id": user_id, "operation": "create_snapshot"}
            )
            raise

    async def get_snapshot(self, session_id: str) -> Optional[StateSnapshot]:
        """获取状态快照"""
        start_time = asyncio.get_event_loop().time()

        try:
            snapshot_data = None

            # 尝试从Redis获取
            if self.redis:
                snapshot_data = await self.redis.get(f"snapshot:{session_id}")

            # 如果Redis中没有，尝试从内存获取
            if not snapshot_data and session_id in self.snapshots_in_memory:
                snapshot = self.snapshots_in_memory[session_id]

                # 检查是否过期
                if snapshot.expires_at > datetime.utcnow():
                    structured_logger.log_info(
                        "Retrieved snapshot from memory backup",
                        extra={"session_id": session_id, "snapshot_id": snapshot.snapshot_id},
                    )
                    return snapshot
                else:
                    # 清理过期快照
                    del self.snapshots_in_memory[session_id]

            if not snapshot_data:
                structured_logger.log_info("No snapshot found for session", extra={"session_id": session_id})
                return None

            # 反序列化
            snapshot_dict = json.loads(snapshot_data)
            snapshot = StateSnapshot(**snapshot_dict)

            # 检查是否过期
            if snapshot.expires_at <= datetime.utcnow():
                await self.delete_snapshot(session_id)
                structured_logger.log_info(
                    "Snapshot expired and deleted",
                    extra={
                        "session_id": session_id,
                        "snapshot_id": snapshot.snapshot_id,
                        "expired_at": snapshot.expires_at.isoformat(),
                    },
                )
                return None

            # 更新内存备份
            self.snapshots_in_memory[session_id] = snapshot

            # 记录指标
            retrieval_time = asyncio.get_event_loop().time() - start_time
            metrics_collector.record_histogram("snapshot_retrieval_time_ms", retrieval_time * 1000)

            structured_logger.log_info(
                "State snapshot retrieved successfully",
                extra={
                    "snapshot_id": snapshot.snapshot_id,
                    "session_id": session_id,
                    "retrieval_time_ms": retrieval_time * 1000,
                },
            )

            return snapshot

        except Exception as e:
            structured_logger.log_error(e, extra={"session_id": session_id, "operation": "get_snapshot"})
            return None

    async def delete_snapshot(self, session_id: str) -> bool:
        """删除状态快照"""
        try:
            # 从Redis删除
            if self.redis:
                await self.redis.delete(f"snapshot:{session_id}")

            # 从内存删除
            if session_id in self.snapshots_in_memory:
                del self.snapshots_in_memory[session_id]

            metrics_collector.increment_counter("snapshots_deleted_total", 1)

            structured_logger.log_info("State snapshot deleted successfully", extra={"session_id": session_id})

            return True

        except Exception as e:
            structured_logger.log_error(e, extra={"session_id": session_id, "operation": "delete_snapshot"})
            return False

    async def cleanup_expired_snapshots(self) -> int:
        """清理过期快照"""
        cleaned_count = 0

        try:
            # 清理内存中的过期快照
            now = datetime.utcnow()
            expired_sessions = []

            for session_id, snapshot in self.snapshots_in_memory.items():
                if snapshot.expires_at <= now:
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                del self.snapshots_in_memory[session_id]
                cleaned_count += 1

            if self.redis:
                # 清理Redis中的过期快照（Redis会自动过期，这里只是记录）
                keys = await self.redis.keys("snapshot:*")
                total_snapshots = len(keys)
                structured_logger.log_info("Redis snapshots count", extra={"total_redis_snapshots": total_snapshots})

            metrics_collector.increment_counter("snapshot_cleanup_runs_total", 1, {"cleaned_count": cleaned_count})

            structured_logger.log_info(
                "Expired snapshots cleanup completed",
                extra={"cleaned_count": cleaned_count, "remaining_memory_snapshots": len(self.snapshots_in_memory)},
            )

            return cleaned_count

        except Exception as e:
            structured_logger.log_error(e, extra={"operation": "cleanup_expired_snapshots"})
            return 0

    async def get_session_snapshots(self, user_id: str) -> List[StateSnapshot]:
        """获取用户的所有快照"""
        try:
            snapshots = []

            # 从内存中获取
            for session_id, snapshot in self.snapshots_in_memory.items():
                if snapshot.user_id == user_id and snapshot.expires_at > datetime.utcnow():
                    snapshots.append(snapshot)

            # 如果有Redis，也从Redis获取
            if self.redis:
                keys = await self.redis.keys("snapshot:*")
                for key in keys:
                    data = await self.redis.get(key)
                    if data:
                        snapshot_dict = json.loads(data)
                        snapshot = StateSnapshot(**snapshot_dict)
                        if (
                            snapshot.user_id == user_id
                            and snapshot.expires_at > datetime.utcnow()
                            and snapshot.snapshot_id not in [s.snapshot_id for s in snapshots]
                        ):
                            snapshots.append(snapshot)

            # 按创建时间排序
            snapshots.sort(key=lambda x: x.created_at, reverse=True)

            return snapshots

        except Exception as e:
            structured_logger.log_error(e, extra={"user_id": user_id, "operation": "get_session_snapshots"})
            return []


# 全局实例
state_snapshot_service = StateSnapshotService()
