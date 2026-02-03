import time
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from app.infra.gateway.schemas import ModelConfig
from app.infra.cache.redis_client import redis_client

logger = logging.getLogger(__name__)

@dataclass
class ModelMetadata:
    provider: str
    model_name: str
    input_cost_per_1k: float  # In USD
    output_cost_per_1k: float # In USD
    avg_latency_ms: float = 0.0
    quality_score: float = 0.0 # 0.0 to 10.0
    success_rate: float = 1.0
    negative_feedback_streak: int = 0
    total_calls: int = 0
    last_updated: float = 0.0
    supported_features: List[str] = field(default_factory=list) # e.g., ["json_mode", "function_calling"]
    status: str = "ACTIVE"  # SHADOW | CANDIDATE | ACTIVE | PRIMARY | QUARANTINED
    lifecycle_action: str = "KEEP"
    anomaly_severity: str = "NONE"
    anomaly_reason: str = "stable"
    anomaly_drop: float = 0.0

class ModelRegistry:
    """
    Central registry for available models and their metadata.
    Supports hot-reloading of configurations and Redis-backed persistent scoring.
    """
    
    def __init__(self):
        self._models: Dict[str, ModelMetadata] = {}
        self._configs: Dict[str, ModelConfig] = {}
        # Buffer for debounce strategy: key -> list of feedback scores
        self._feedback_buffer: Dict[str, List[float]] = {}
        self._last_flush_time: Dict[str, float] = {}
        self._buffer_threshold = 10
        self._flush_interval = 5.0 # seconds
        self._replay_queue: List[Tuple[str, List[float], str]] = []
        self._replay_task: Optional[asyncio.Task] = None
        self._intent_counts: Dict[str, Dict[str, int]] = {}
        self._success_window = 1000

        # Load default models (Hard-coded defaults)
        self._load_defaults()

    async def initialize(self):
        """
        Async initialization: Load persistent scores from Redis (Hot Start).
        If Redis is empty, syncs defaults to Redis.
        """
        logger.info("Initializing ModelRegistry with Redis persistence...")
        await redis_client.initialize()
        
        for key, meta in self._models.items():
            # Init buffer state
            self._feedback_buffer[key] = []
            self._last_flush_time[key] = time.time()
            self._intent_counts[key] = {}
            
            redis_key = f"salesboost:model:reputation:{key}"
            try:
                # Try to load from Redis
                data = await redis_client.hgetall(redis_key)
                if data:
                    meta.quality_score = float(data.get("quality_score", meta.quality_score))
                    meta.negative_feedback_streak = int(data.get("negative_streak", meta.negative_feedback_streak))
                    meta.total_calls = int(data.get("total_calls", meta.total_calls))
                    meta.last_updated = float(data.get("last_updated", meta.last_updated))
                    meta.status = data.get("status", meta.status) or meta.status
                    meta.lifecycle_action = data.get("lifecycle_action", meta.lifecycle_action) or meta.lifecycle_action
                    meta.anomaly_severity = data.get("anomaly_severity", meta.anomaly_severity) or meta.anomaly_severity
                    meta.anomaly_reason = data.get("anomaly_reason", meta.anomaly_reason) or meta.anomaly_reason
                    try:
                        meta.anomaly_drop = float(data.get("anomaly_drop", meta.anomaly_drop))
                    except (TypeError, ValueError):
                        meta.anomaly_drop = meta.anomaly_drop
                    logger.debug(f"Loaded {key} from Redis: Score={meta.quality_score}")
                else:
                    # Sync default to Redis if missing
                    await self._sync_to_redis(key, meta)
            except Exception as e:
                logger.error(f"Failed to load {key} from Redis: {e}")
        if self._replay_task is None or self._replay_task.done():
            self._replay_task = asyncio.create_task(self._replay_worker())

    async def _sync_to_redis(self, key: str, meta: ModelMetadata):
        """Sync current in-memory state to Redis (for initialization/fallback recovery)"""
        redis_key = f"salesboost:model:reputation:{key}"
        mapping = {
            "quality_score": str(meta.quality_score),
            "negative_streak": str(meta.negative_feedback_streak),
            "total_calls": str(meta.total_calls),
            "last_updated": str(time.time()),
            "status": meta.status,
            "lifecycle_action": meta.lifecycle_action,
            "anomaly_severity": meta.anomaly_severity,
            "anomaly_reason": meta.anomaly_reason,
            "anomaly_drop": str(meta.anomaly_drop),
        }
        await redis_client.hset(redis_key, mapping)

    async def update_model_reputation(self, provider: str, model_name: str, feedback_score: float):
        """
        Feedback Loop: Update quality score based on user feedback.
        Uses In-Memory update immediately + Async Batched Redis Update (Debounce).
        
        feedback_score: 1.0 (Like) or -1.0 (Dislike)
        """
        key = f"{provider}/{model_name}"
        if key not in self._models:
            return
            
        meta = self._models[key]
        
        # 1. Immediate Local Update (for responsiveness)
        target_score = 10.0 if feedback_score > 0 else 0.0
        alpha = 0.05
        
        # Simple local approximation for UI/Routing immediate effect
        # Note: True source of truth is eventually consistent via Redis
        if feedback_score < 0:
            meta.negative_feedback_streak += 1
        else:
            meta.negative_feedback_streak = 0
            
        meta.quality_score = (1 - alpha) * meta.quality_score + alpha * target_score
        
        # Penalty Logic
        if meta.negative_feedback_streak >= 5:
            meta.quality_score *= 0.5
            meta.negative_feedback_streak = 0
            
        meta.quality_score = max(0.1, min(10.0, meta.quality_score))
        meta.total_calls += 1
        meta.last_updated = time.time()
        
        # 2. Add to Buffer
        if key not in self._feedback_buffer:
            self._feedback_buffer[key] = []
        self._feedback_buffer[key].append(feedback_score)
        
        # 3. Check Flush Conditions
        now = time.time()
        should_flush = (
            len(self._feedback_buffer[key]) >= self._buffer_threshold or 
            (now - self._last_flush_time.get(key, 0)) >= self._flush_interval
        )
        
        if should_flush:
            # Trigger async flush (fire and forget)
            # We copy the buffer to avoid race conditions if we were using threads, 
            # but in asyncio we are single-threaded so it's safer, yet good practice to clear immediately.
            batch = self._feedback_buffer[key][:]
            self._feedback_buffer[key] = []
            self._last_flush_time[key] = now
            
            # Use ensure_future/create_task to run in background
            batch_id = f"{key}:{int(now * 1000)}"
            asyncio.create_task(self._flush_batch_to_redis(key, batch, batch_id=batch_id))

    async def update_metrics(
        self,
        provider: str,
        model_name: str,
        latency_ms: float,
        success: bool,
        intent_category: Optional[str] = None,
        shadow: bool = False,
    ):
        key = f"{provider}/{model_name}"
        if key not in self._models:
            return
        meta = self._models[key]
        if not shadow and meta.status != "SHADOW":
            meta.avg_latency_ms = (meta.avg_latency_ms * 0.9) + (latency_ms * 0.1)
            meta.success_rate = (meta.success_rate * 0.95) + (0.05 if success else 0.0)
            meta.total_calls += 1
            meta.last_updated = time.time()
            await self._record_success(key, success)
            if intent_category:
                await self._record_intent(key, intent_category)

    async def _record_success(self, key: str, success: bool):
        redis_key = f"salesboost:model:success:{key}"
        value = "1" if success else "0"
        try:
            await redis_client.lpush(redis_key, value)
            await redis_client.ltrim(redis_key, 0, self._success_window - 1)
        except Exception:
            # Best effort; ignore if Redis is down.
            pass

    async def _record_intent(self, key: str, intent_category: str):
        redis_key = f"salesboost:model:intents:{key}"
        intent_counts = self._intent_counts.setdefault(key, {})
        intent_counts[intent_category] = intent_counts.get(intent_category, 0) + 1
        try:
            await redis_client.hset(redis_key, {"intent": intent_category, "count": intent_counts[intent_category]})
        except Exception:
            pass

    async def _flush_batch_to_redis(self, key: str, batch: List[float], batch_id: Optional[str] = None):
        """
        Execute batch update via Lua script.
        """
        if not batch:
            return
            
        redis_key = f"salesboost:model:reputation:{key}"
        alpha = 0.05
        current_time = time.time()
        
        # Calculate counts for batch processing in Lua
        # We pass the full list of targets or just counts. 
        # Passing full list allows Lua to iterate exactly.
        # Format for Lua: comma separated string or multiple ARGV?
        # Let's pass as a string "1.0,-1.0,1.0"
        targets_str = ",".join(["10.0" if s > 0 else "0.0" for s in batch])
        
        # Lua Script for Batch EWMA (unit-test friendly arg order)
        lua_script = """
        local key = KEYS[1]
        local targets_str = ARGV[1]
        local alpha = tonumber(ARGV[2])
        local default_score = tonumber(ARGV[3])
        local timestamp = ARGV[4]
        
        -- Helper split function
        local function split(s, delimiter)
            local result = {};
            for match in (s..delimiter):gmatch("(.-)"..delimiter) do
                table.insert(result, match);
            end
            return result;
        end
        
        -- Get current state
        local current_score = redis.call('HGET', key, 'quality_score')
        local streak = redis.call('HGET', key, 'negative_streak')
        local calls = redis.call('HGET', key, 'total_calls')
        
        if not current_score then current_score = default_score else current_score = tonumber(current_score) end
        if not streak then streak = 0 else streak = tonumber(streak) end
        if not calls then calls = 0 else calls = tonumber(calls) end
        
        local targets = split(targets_str, ",")
        local last_score = current_score
        
        for _, target_val in ipairs(targets) do
            local target = tonumber(target_val)
            
            -- Update Streak
            if target < 5.0 then
                streak = streak + 1
            else
                streak = 0
            end
            
            -- EWMA
            current_score = (1 - alpha) * current_score + alpha * target
            
            -- Penalty
            if streak >= 5 then
                current_score = current_score * 0.5
                streak = 0
            end
            
            calls = calls + 1
        end
        
        -- Bounds
        if current_score > 10.0 then current_score = 10.0 end
        if current_score < 0.1 then current_score = 0.1 end
        
        redis.call('HMSET', key, 'quality_score', current_score, 'negative_streak', streak, 'total_calls', calls, 'last_updated', timestamp)
        
        -- Log History (Only log the final state of this batch to save space)
        redis.call('RPUSH', 'salesboost:model:history:' .. key, timestamp .. ":" .. current_score)
        redis.call('LTRIM', 'salesboost:model:history:' .. key, -1000, -1)
        
        return {tostring(current_score), tostring(streak), tostring(calls)}
        """
        
        meta = self._models.get(key)
        # Fallback default score
        default_score = meta.quality_score if meta else 5.0
        
        try:
            result = await redis_client.eval(
                lua_script,
                1,
                redis_key,
                targets_str,
                alpha,
                default_score,
                current_time,
            )
            
            if not result:
                self._replay_queue.append((key, batch, batch_id))
                return

            if result and meta:
                # Re-sync local state with Redis authoritative state
                # This corrects any drift from local approximations
                if result[0] != "SKIP":
                    meta.quality_score = float(result[0])
                    meta.negative_feedback_streak = int(result[1])
                    meta.total_calls = int(result[2])
                    meta.last_updated = current_time
        except Exception as e:
            logger.error(f"Error flushing batch for {key}: {e}")
            # Queue for replay when Redis is healthy again.
            batch_id = batch_id or f"{key}:{int(current_time*1000)}"
            self._replay_queue.append((key, batch, batch_id))

    async def _replay_worker(self):
        while True:
            try:
                healthy = await redis_client.is_healthy()
                if healthy and self._replay_queue:
                    batch_copy = self._replay_queue[:]
                    self._replay_queue = []
                    for key, batch, batch_id in batch_copy:
                        await self._flush_batch_to_redis(key, batch, batch_id=batch_id)
                await asyncio.sleep(2.0)
            except Exception as exc:
                logger.warning("Replay worker error: %s", exc)
                await asyncio.sleep(5.0)

    def get_intent_weight(self, provider: str, model_name: str) -> float:
        key = f"{provider}/{model_name}"
        counts = self._intent_counts.get(key, {})
        total = sum(counts.values())
        if total == 0:
            return 1.0
        weights = {
            "LOGIC": 1.2,
            "EXTRACTION": 1.2,
            "COMPLIANCE": 1.2,
            "SIMPLE_CHAT": 1.0,
            "CREATIVE": 0.8,
        }
        score = 0.0
        for intent, count in counts.items():
            score += weights.get(intent.upper(), 1.0) * (count / total)
        return round(score, 3)

    async def get_success_rate(self, provider: str, model_name: str) -> float:
        key = f"{provider}/{model_name}"
        redis_key = f"salesboost:model:success:{key}"
        try:
            data = await redis_client.lrange(redis_key, 0, self._success_window - 1)
            if data:
                successes = sum(1 for x in data if str(x) == "1")
                return round(successes / len(data), 3)
        except Exception:
            pass
        meta = self._models.get(key)
        return round(meta.success_rate if meta else 1.0, 3)

    async def apply_lifecycle_actions(self, actions: Dict[str, str], primary_key: Optional[str]) -> None:
        """Apply lifecycle decisions and persist status changes."""
        current_primary = primary_key or self.get_primary_key()
        for key, action in actions.items():
            meta = self._models.get(key)
            if not meta:
                continue
            if action == "QUARANTINE":
                meta.status = "QUARANTINED"
            elif action == "PROMOTE_CANDIDATE":
                meta.status = "CANDIDATE"
            elif action == "PROMOTE_PRIMARY":
                if current_primary and current_primary in self._models:
                    self._models[current_primary].status = "ACTIVE"
                    await self._persist_status(current_primary, self._models[current_primary].status)
                meta.status = "PRIMARY"
                current_primary = key
            elif action == "DEMOTE_ACTIVE":
                if meta.status == "PRIMARY":
                    meta.status = "ACTIVE"
            await self._persist_status(key, meta.status)

    async def _persist_status(self, key: str, status: str) -> None:
        redis_key = f"salesboost:model:reputation:{key}"
        try:
            await redis_client.hset(redis_key, {"status": status})
        except Exception:
            pass

    async def set_lifecycle_action(self, key: str, action: str) -> None:
        meta = self._models.get(key)
        if meta:
            meta.lifecycle_action = action
        redis_key = f"salesboost:model:reputation:{key}"
        try:
            await redis_client.hset(redis_key, {"lifecycle_action": action})
        except Exception:
            pass

    def get_lifecycle_action(self, key: str) -> str:
        meta = self._models.get(key)
        return meta.lifecycle_action if meta else "KEEP"

    async def set_anomaly(self, key: str, anomaly: Dict[str, str]) -> None:
        meta = self._models.get(key)
        if meta:
            meta.anomaly_severity = anomaly.get("severity", meta.anomaly_severity)
            meta.anomaly_reason = anomaly.get("reason", meta.anomaly_reason)
            try:
                meta.anomaly_drop = float(anomaly.get("drop", meta.anomaly_drop))
            except (TypeError, ValueError):
                meta.anomaly_drop = meta.anomaly_drop
        redis_key = f"salesboost:model:reputation:{key}"
        try:
            await redis_client.hset(
                redis_key,
                {
                    "anomaly_severity": anomaly.get("severity", "NONE"),
                    "anomaly_reason": anomaly.get("reason", "stable"),
                    "anomaly_drop": anomaly.get("drop", "0.0"),
                },
            )
        except Exception:
            pass

    def get_anomaly(self, key: str) -> Dict[str, str]:
        meta = self._models.get(key)
        if not meta:
            return {"severity": "NONE", "reason": "unknown", "drop": "0.0"}
        return {
            "severity": meta.anomaly_severity,
            "reason": meta.anomaly_reason,
            "drop": str(meta.anomaly_drop),
        }

    def get_primary_key(self) -> Optional[str]:
        for key, meta in self._models.items():
            if meta.status == "PRIMARY":
                return key
        if not self._models:
            return None
        return max(self._models.items(), key=lambda item: item[1].quality_score)[0]

    def set_primary(self, provider: str, model_name: str) -> None:
        key = f"{provider}/{model_name}"
        if key not in self._models:
            return
        for meta in self._models.values():
            if meta.status == "PRIMARY":
                meta.status = "ACTIVE"
        self._models[key].status = "PRIMARY"

    def register_model(self, metadata: ModelMetadata):
        key = f"{metadata.provider}/{metadata.model_name}"
        self._models[key] = metadata
        self._configs[key] = ModelConfig(
            provider=metadata.provider,
            model_name=metadata.model_name
        )

    def list_models(self) -> List[ModelMetadata]:
        return list(self._models.values())

    def get_model(self, provider: str, model_name: str) -> Optional[ModelMetadata]:
        key = f"{provider}/{model_name}"
        return self._models.get(key)

    def _load_defaults(self):
        # Initialize with some default known models
        # OpenAI / DeepSeek
        self.register_model(ModelMetadata(
            provider="openai",
            model_name="gpt-4o",
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
            quality_score=9.5,
            avg_latency_ms=800,
            status="PRIMARY",
        ))
        self.register_model(ModelMetadata(
            provider="openai",
            model_name="gpt-3.5-turbo",
            input_cost_per_1k=0.0005,
            output_cost_per_1k=0.0015,
            quality_score=7.0,
            avg_latency_ms=300
        ))
        # DeepSeek (SiliconFlow or Direct)
        self.register_model(ModelMetadata(
            provider="deepseek",
            model_name="deepseek-chat",
            input_cost_per_1k=0.0001,
            output_cost_per_1k=0.0002,
            quality_score=8.5,
            avg_latency_ms=500
        ))
        # Gemini
        self.register_model(ModelMetadata(
            provider="google",
            model_name="gemini-2.0-flash",
            input_cost_per_1k=0.0001,
            output_cost_per_1k=0.0001,
            quality_score=8.8,
            avg_latency_ms=400
        ))
        # Claude (via Bedrock or Anthropic)
        self.register_model(ModelMetadata(
            provider="anthropic",
            model_name="claude-3-5-sonnet",
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
            quality_score=9.6,
            avg_latency_ms=1000
        ))

# Global Instance
model_registry = ModelRegistry()
