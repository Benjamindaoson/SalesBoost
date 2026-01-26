import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.trace import KnowledgeEvidence
from app.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)


class KnowledgeAsset(BaseModel):
    id: str
    content: str
    source: str
    version: str = "1.0"
    valid_until: Optional[datetime] = None
    reliability: float = 1.0
    tags: List[str] = Field(default_factory=list)


class KnowledgeEngine:
    """
    Knowledge engine backed by a persistent vector store.
    """

    def __init__(self) -> None:
        self._service = KnowledgeService()

    def add_asset(self, asset: KnowledgeAsset) -> str:
        meta = {
            "source": asset.source,
            "version": asset.version,
            "reliability": asset.reliability,
            "tags": asset.tags,
            "valid_until": asset.valid_until.isoformat() if asset.valid_until else None,
        }
        return self._service.add_document(asset.content, meta=meta, doc_id=asset.id)

    def retrieve(self, query: str, top_k: int = 3) -> List[KnowledgeEvidence]:
        now = datetime.utcnow()
        results = self._service.query(query, top_k=top_k)
        evidences: List[KnowledgeEvidence] = []
        for idx, item in enumerate(results):
            meta = item.get("metadata") or {}
            valid_until = meta.get("valid_until")
            if valid_until:
                try:
                    if datetime.fromisoformat(valid_until) < now:
                        continue
                except ValueError:
                    pass
            reliability = float(meta.get("reliability", 1.0))
            if reliability < 0.6:
                continue
            distance = float(item.get("distance") or 0.0)
            confidence = max(0.0, min(1.0, 1.0 - distance))
            evidences.append(
                KnowledgeEvidence(
                    evidence_id=meta.get("doc_id", f"doc-{idx}"),
                    source=meta.get("source", "unknown"),
                    content_snippet=(item.get("content") or "")[:200],
                    confidence=confidence if reliability >= 0.6 else 0.0,
                    metadata={
                        "version": meta.get("version", "1.0"),
                        "tags": meta.get("tags", []),
                        "reliability": reliability,
                    },
                )
            )
            if len(evidences) >= top_k:
                break
        return evidences

    def format_for_prompt(self, evidences: List[KnowledgeEvidence]) -> str:
        if not evidences:
            return "No relevant evidence found."
        lines = ["Use the following evidence (cite [ID] for key claims):"]
        for ev in evidences:
            risk_label = "[verify]" if ev.metadata.get("reliability", 1.0) < 0.8 else ""
            lines.append(
                f"[{ev.evidence_id}]{risk_label} (source={ev.source}, conf={ev.confidence:.2f}): {ev.content_snippet}"
            )
        return "\n".join(lines)


knowledge_engine = KnowledgeEngine()
