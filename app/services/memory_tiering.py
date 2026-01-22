import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MemoryRecord:
    content: str
    timestamp: str
    metadata: Dict[str, Any]
    score: float = 0.0


class MemoryTierManager:
    """
    记忆分层管理器（Episodic / Semantic / Procedural）
    - Episodic: 交互片段与时间线
    - Semantic: 抽象事实与稳定知识
    - Procedural: SOP/流程型指导
    """

    def __init__(self, base_dir: str = "data/memory"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def add_episode(
        self,
        user_id: str,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        store = self._load_store(user_id)
        record = MemoryRecord(
            content=content,
            timestamp=datetime.utcnow().isoformat(),
            metadata={"session_id": session_id, **(metadata or {})},
        )
        store["episodic"].append(asdict(record))
        self._save_store(user_id, store)

    def consolidate(self, user_id: str) -> None:
        """
        将 episodic 中的高价值信息固化到 semantic/procedural。
        轻量启发式：数字/条款/风险 => semantic；步骤/流程/如何 => procedural
        """
        store = self._load_store(user_id)
        episodic = store.get("episodic", [])
        if not episodic:
            return

        semantic, procedural = store.get("semantic", []), store.get("procedural", [])
        for item in episodic[-50:]:
            content = item.get("content", "")
            if self._is_procedural(content):
                procedural.append(self._to_record(content, item.get("metadata", {})))
            if self._is_semantic(content):
                semantic.append(self._to_record(content, item.get("metadata", {})))

        store["semantic"] = self._dedupe_records(semantic)
        store["procedural"] = self._dedupe_records(procedural)
        self._save_store(user_id, store)

    def retrieve(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> Dict[str, List[MemoryRecord]]:
        store = self._load_store(user_id)
        episodic = self._rank(store.get("episodic", []), query, top_k)
        semantic = self._rank(store.get("semantic", []), query, top_k)
        procedural = self._rank(store.get("procedural", []), query, top_k)
        return {
            "episodic": episodic,
            "semantic": semantic,
            "procedural": procedural,
        }

    def _rank(self, records: List[Dict[str, Any]], query: str, top_k: int) -> List[MemoryRecord]:
        if not records:
            return []
        query_terms = self._tokenize(query)
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for record in records:
            content = record.get("content", "")
            tokens = self._tokenize(content)
            overlap = len(query_terms.intersection(tokens))
            score = overlap / max(len(query_terms), 1)
            scored.append((score, record))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            MemoryRecord(
                content=item["content"],
                timestamp=item.get("timestamp", ""),
                metadata=item.get("metadata", {}),
                score=score,
            )
            for score, item in scored[:top_k]
            if score > 0
        ]

    def _to_record(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(
            MemoryRecord(
                content=content,
                timestamp=datetime.utcnow().isoformat(),
                metadata=metadata,
            )
        )

    def _is_procedural(self, content: str) -> bool:
        keywords = ["步骤", "流程", "如何", "怎么办", "操作", "SOP"]
        return any(k in content for k in keywords)

    def _is_semantic(self, content: str) -> bool:
        keywords = ["费率", "年费", "额度", "条款", "合规", "风险", "期限", "%"]
        return any(k in content for k in keywords) or any(char.isdigit() for char in content)

    def _tokenize(self, text: str) -> set[str]:
        tokens = [t.strip().lower() for t in text.replace("。", " ").replace(",", " ").split()]
        return {t for t in tokens if t}

    def _dedupe_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        deduped = []
        for record in records:
            content = record.get("content", "")
            if content and content not in seen:
                seen.add(content)
                deduped.append(record)
        return deduped[-200:]

    def _store_path(self, user_id: str) -> Path:
        return self.base_dir / f"{user_id}.json"

    def _load_store(self, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        path = self._store_path(user_id)
        if not path.exists():
            return {"episodic": [], "semantic": [], "procedural": []}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load memory store for {user_id}: {e}")
            return {"episodic": [], "semantic": [], "procedural": []}

    def _save_store(self, user_id: str, store: Dict[str, List[Dict[str, Any]]]) -> None:
        path = self._store_path(user_id)
        tmp_path = path.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
        tmp_path.replace(path)
