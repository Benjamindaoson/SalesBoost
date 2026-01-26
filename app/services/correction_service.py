import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.services.knowledge_service import KnowledgeService
from app.services.graph_rag_service import GraphRAGService

logger = logging.getLogger(__name__)


class CorrectionService:
    """Handles RAG correction feedback and immediate index updates."""

    def __init__(self, log_path: str = "./data/corrections.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge = KnowledgeService()
        self.graph = GraphRAGService()

    def record(self, payload: Dict[str, Any]):
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    async def apply(self, correction: Dict[str, Any]) -> Dict[str, Any]:
        chunk_id = correction.get("chunk_id") or correction.get("doc_id")
        corrected_text = correction.get("corrected_text")
        meta = correction.get("metadata", {})
        reason = correction.get("reason")
        if not chunk_id or not corrected_text:
            raise ValueError("chunk_id and corrected_text are required")

        # Upsert vector
        self.knowledge.upsert_document(content=corrected_text, meta=meta, doc_id=chunk_id)

        # Update GraphRAG (best-effort)
        graph_stats = {}
        try:
            graph_stats = await self.graph.ingest_document(doc_id=chunk_id, text=corrected_text, metadata=meta)
        except Exception as e:
            logger.warning(f"Graph ingestion for correction failed: {e}")

        self.record({"chunk_id": chunk_id, "reason": reason, "meta": meta})
        return {"chunk_id": chunk_id, "graph": graph_stats}


correction_service = CorrectionService()
