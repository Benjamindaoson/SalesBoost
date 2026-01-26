"""
Simplified State Snapshot Service - 简化状态快照服务
使用内存存储，避免复杂的数据库依赖问题
"""

import json
import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import uuid
import logging

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
    created_at: float  # 使用时间戳
    expires_at: float


class SimpleStateSnapshotService:
    """简化的状态快照服务（内存存储）"""

    def __init__(self):
        self.snapshots = {}  # session_id -> snapshot
        self.cleanup_task = None
        self.running = False

    async def initialize(self):
        """初始化服务"""
        self.running = True
        # 启动清理任务
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("SimpleStateSnapshotService initialized")

    async def stop(self):
        """停止服务"""
        self.running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("SimpleStateSnapshotService stopped")

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
        start_time = time.time()

        try:
            snapshot_id = str(uuid.uuid4())
            now = time.time()
            expires_at = now + (ttl_hours * 3600)

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

            # 保存到内存
            self.snapshots[session_id] = snapshot

            creation_time = time.time() - start_time
            logger.info(f"State snapshot created: {snapshot_id} for session {session_id} in {creation_time:.3f}s")

            return snapshot_id

        except Exception as e:
            logger.error(f"Failed to create snapshot for session {session_id}: {e}")
            raise

    async def get_snapshot(self, session_id: str) -> Optional[StateSnapshot]:
        """获取状态快照"""
        try:
            snapshot = self.snapshots.get(session_id)

            if not snapshot:
                logger.info(f"No snapshot found for session {session_id}")
                return None

            # 检查是否过期
            if snapshot.expires_at <= time.time():
                await self.delete_snapshot(session_id)
                logger.info(f"Snapshot expired and deleted for session {session_id}")
                return None

            logger.info(f"Snapshot retrieved for session {session_id}")
            return snapshot

        except Exception as e:
            logger.error(f"Failed to get snapshot for session {session_id}: {e}")
            return None

    async def delete_snapshot(self, session_id: str) -> bool:
        """删除状态快照"""
        try:
            if session_id in self.snapshots:
                del self.snapshots[session_id]
                logger.info(f"Snapshot deleted for session {session_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete snapshot for session {session_id}: {e}")
            return False

    async def cleanup_expired_snapshots(self) -> int:
        """清理过期快照"""
        cleaned_count = 0
        current_time = time.time()

        try:
            expired_sessions = []

            for session_id, snapshot in self.snapshots.items():
                if snapshot.expires_at <= current_time:
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                del self.snapshots[session_id]
                cleaned_count += 1

            logger.info(f"Cleaned up {cleaned_count} expired snapshots")
            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired snapshots: {e}")
            return 0

    async def _periodic_cleanup(self):
        """定期清理过期快照"""
        while self.running:
            try:
                await self.cleanup_expired_snapshots()
                # 每小时清理一次
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(60)  # 出错时1分钟后重试

    async def get_session_snapshots(self, user_id: str) -> List[StateSnapshot]:
        """获取用户的所有快照"""
        try:
            current_time = time.time()
            snapshots = []

            for session_id, snapshot in self.snapshots.items():
                if snapshot.user_id == user_id and snapshot.expires_at > current_time:
                    snapshots.append(snapshot)

            # 按创建时间排序
            snapshots.sort(key=lambda x: x.created_at, reverse=True)

            logger.info(f"Found {len(snapshots)} snapshots for user {user_id}")
            return snapshots

        except Exception as e:
            logger.error(f"Failed to get snapshots for user {user_id}: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        current_time = time.time()
        total_snapshots = len(self.snapshots)
        expired_snapshots = sum(1 for s in self.snapshots.values() if s.expires_at <= current_time)

        return {
            "total_snapshots": total_snapshots,
            "active_snapshots": total_snapshots - expired_snapshots,
            "expired_snapshots": expired_snapshots,
            "running": self.running,
        }


# 全局实例
simple_state_snapshot_service = SimpleStateSnapshotService()
