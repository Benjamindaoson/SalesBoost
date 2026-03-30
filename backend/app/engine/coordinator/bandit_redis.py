import random
import uuid
from typing import Any, Dict, Iterable

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    redis = None


class RedisContextualBandit:
    def __init__(self, redis_url: str, epsilon: float = 0.1, key_prefix: str = "bandit") -> None:
        if redis is None:
            raise RuntimeError("redis is required for RedisContextualBandit")
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._epsilon = max(0.0, min(1.0, epsilon))
        self._key_prefix = key_prefix

    def choose(self, context: Dict[str, Any], candidates: Iterable[str]) -> Dict[str, Any]:
        arms = [c for c in candidates if isinstance(c, str)]
        if not arms:
            return {
                "decision_id": uuid.uuid4().hex,
                "chosen": "npc",
                "score": 0.0,
                "exploration": True,
            }

        exploration = random.random() < self._epsilon
        if exploration:
            best_arm = random.choice(arms)
            best_score = self._get_score(best_arm)
        else:
            # Redis-backed scoring (simple mean reward per arm)
            best_arm = arms[0]
            best_score = self._get_score(best_arm)
            for arm in arms[1:]:
                score = self._get_score(arm)
                if score > best_score:
                    best_arm = arm
                    best_score = score

        decision_id = uuid.uuid4().hex
        return {
            "decision_id": decision_id,
            "chosen": best_arm,
            "score": round(best_score, 4),
            "exploration": exploration,
        }

    def record_feedback(self, decision_id: str, chosen: str, reward: float) -> None:
        key = f"{self._key_prefix}:{chosen}"
        data = self._client.hgetall(key) or {}
        count = float(data.get("count", 0.0))
        value = float(data.get("value", 0.0))
        new_value = (value * count + reward) / (count + 1.0)
        self._client.hset(key, mapping={"count": count + 1.0, "value": new_value})

    def _get_score(self, arm: str) -> float:
        data = self._client.hgetall(f"{self._key_prefix}:{arm}") or {}
        return float(data.get("value", 0.0))
