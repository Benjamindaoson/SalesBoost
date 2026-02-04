import logging
import json
from datetime import datetime

from app.schemas.blackboard import (
    BlackboardSchema, 
    SalesStageEstimate, 
    CustomerPsychology, 
    StateConfidence
)
from core.redis import get_redis, InMemoryCache

logger = logging.getLogger(__name__)

class Librarian:
    """
    Librarian (Context Manager) - 系统的“黑板管理者”
    负责维护 Blackboard 状态，执行状态估计，并确保数据持久化。
    """
    
    def __init__(self):
        self._redis_prefix = "blackboard:"

    async def get_blackboard(self, session_id: str, user_id: str) -> BlackboardSchema:
        """获取或初始化黑板状态"""
        redis = await get_redis()
        key = f"{self._redis_prefix}{session_id}"
        
        try:
            if isinstance(redis, InMemoryCache):
                raw = getattr(redis, "_store", {}).get(key)
            else:
                raw = await redis.get(key)
                
            if raw:
                data = json.loads(raw)
                return BlackboardSchema(**data)
        except Exception as e:
            logger.warning(f"Failed to load blackboard for session {session_id}: {e}")

        # 初始化新黑板
        default_confidence = StateConfidence(value=0.5, method="initialization")
        return BlackboardSchema(
            session_id=session_id,
            user_id=user_id,
            stage_estimate=SalesStageEstimate(
                current="opening",
                confidence=default_confidence
            ),
            psychology=CustomerPsychology(
                trust=0.5,
                resistance=0.3,
                interest=0.5,
                confidence=default_confidence
            )
        )

    async def save_blackboard(self, blackboard: BlackboardSchema) -> None:
        """保存黑板状态到 Redis (原子性更新)"""
        redis = await get_redis()
        key = f"{self._redis_prefix}{blackboard.session_id}"
        lock_key = f"lock:{key}"
        
        try:
            # 只有在非内存模式下才使用分布式锁
            if not isinstance(redis, InMemoryCache):
                async with redis.lock(lock_key, timeout=5):
                    data = blackboard.model_dump_json()
                    await redis.set(key, data)
            else:
                data = blackboard.model_dump_json()
                await redis.set(key, data)
                
            # 发布更新事件
            stream_key = f"stream:blackboard_update:{blackboard.session_id}"
            if not isinstance(redis, InMemoryCache):
                await redis.xadd(stream_key, {"session_id": blackboard.session_id, "turn": str(blackboard.turn_count)}, maxlen=100)
        except Exception as e:
            logger.error(f"Failed to save blackboard for session {blackboard.session_id}: {e}")

    async def estimate_state(self, blackboard: BlackboardSchema, user_input: str, npc_response: str) -> None:
        """
        状态估计 (State Estimation)
        基于对话内容更新客户心理状态和销售阶段。
        目前为启发式实现，后续应接入 LLM。
        """
        # 1. 意图识别与阶段迁移 (启发式)
        lower_input = user_input.lower()
        if any(word in lower_input for word in ["价格", "多少钱", "贵"]):
            blackboard.last_intent = "price_inquiry"
            if blackboard.stage_estimate.current == "opening":
                blackboard.stage_estimate.previous = blackboard.stage_estimate.current
                blackboard.stage_estimate.current = "objection_handling"
                blackboard.stage_estimate.transition_timestamp = datetime.utcnow()
                blackboard.stage_estimate.confidence.value = 0.8
                blackboard.stage_estimate.confidence.method = "rule_based"

        # 2. 心理状态更新 (启发式)
        # 如果客户回复包含积极词汇，提升信任度
        if any(word in npc_response.lower() for word in ["好的", "明白", "有道理"]):
            blackboard.psychology.trust = min(1.0, blackboard.psychology.trust + 0.05)
            blackboard.psychology.interest = min(1.0, blackboard.psychology.interest + 0.05)
            blackboard.psychology.confidence.value = 0.6
        
        # 3. 增加回合数
        blackboard.turn_count += 1
