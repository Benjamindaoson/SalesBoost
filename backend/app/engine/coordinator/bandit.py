import random
import time
import uuid
from typing import Any, Dict, Iterable, Optional


class SimpleContextualBandit:
    def __init__(self, epsilon: float = 0.1) -> None:
        self.epsilon = max(0.0, min(1.0, epsilon))
        self._stats: Dict[str, Dict[str, float]] = {}
        self._decisions: Dict[str, Dict[str, Any]] = {}

    def choose(self, context: Dict[str, Any], candidates: Iterable[str]) -> Dict[str, Any]:
        arms = [c for c in candidates if isinstance(c, str)]
        if not arms:
            return {
                "decision_id": uuid.uuid4().hex,
                "chosen": "npc",
                "score": 0.0,
                "exploration": True,
            }

        exploration = random.random() < self.epsilon
        if exploration:
            chosen = random.choice(arms)
            score = self._score(chosen)
        else:
            scored = [(arm, self._score(arm)) for arm in arms]
            scored.sort(key=lambda item: item[1], reverse=True)
            chosen, score = scored[0]

        decision_id = uuid.uuid4().hex
        self._decisions[decision_id] = {
            "chosen": chosen,
            "context": context,
            "timestamp": time.time(),
        }
        return {
            "decision_id": decision_id,
            "chosen": chosen,
            "score": round(score, 4),
            "exploration": exploration,
        }

    def record_feedback(self, decision_id: str, reward: float, signals: Optional[Dict[str, float]] = None) -> bool:
        decision = self._decisions.pop(decision_id, None)
        if not decision:
            return False
        chosen = decision["chosen"]
        stats = self._stats.setdefault(chosen, {"count": 0.0, "value": 0.0})
        count = stats["count"]
        value = stats["value"]
        new_value = (value * count + reward) / (count + 1.0)
        stats["count"] = count + 1.0
        stats["value"] = new_value
        return True

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        return {k: dict(v) for k, v in self._stats.items()}

    def _score(self, arm: str) -> float:
        stats = self._stats.get(arm)
        if not stats:
            return 0.0
        return stats.get("value", 0.0)
