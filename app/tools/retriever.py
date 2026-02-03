import os
from typing import Any, Dict, Optional, List

from pydantic import Field

from app.infra.gateway.schemas import AgentType
from app.memory.storage.vector_store import VectorStore
from app.tools.base import BaseTool, ToolInputModel
from app.infra.search.vector_store import SearchResult, HybridSearchEngine, BM25Retriever, VectorStore as AsyncVectorStore


class Retriever:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()

    def retrieve(self, query: str, top_k: int = 3) -> str:
        hits = self.vector_store.query(query, n_results=top_k)
        if not hits:
            return ""

        context_parts = []
        for hit in hits:
            content = hit.get("content", "")
            meta = hit.get("metadata", {}) or {}
            source = meta.get("filename", meta.get("source", "unknown"))
            context_parts.append(f"[{source}]: {content}")

        return "\n\n".join(context_parts)


class KnowledgeRetrieverInput(ToolInputModel):
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(3, ge=1, le=20, description="Number of results")
    kb: Optional[str] = Field(None, description="Optional knowledge base collection name")


class KnowledgeRetrieverTool(BaseTool):
    name = "knowledge_retriever"
    description = "Retrieve sales knowledge, product facts, or case studies."
    args_schema = KnowledgeRetrieverInput
    allowed_agents = {
        AgentType.RAG.value,
        AgentType.RETRIEVER.value,
        AgentType.SESSION_DIRECTOR.value,
    }

    def __init__(self, vector_store: Optional[VectorStore] = None) -> None:
        self._vector_store = vector_store
        super().__init__()

    def _get_store(self, kb: Optional[str]) -> VectorStore:
        if kb:
            return VectorStore(collection_name=kb)
        return self._vector_store or VectorStore()

    async def _run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        query = payload["query"]
        top_k = payload.get("top_k", 3)
        kb = payload.get("kb")

        store = self._get_store(kb)
        hits: List[Dict[str, Any]]
        use_hybrid = os.getenv("RAG_HYBRID_ENABLED", "true").lower() in {"1", "true", "yes"}
        if use_hybrid:
            try:
                adapter = _LocalVectorAdapter(store)
                hybrid = HybridSearchEngine(adapter, BM25Retriever())
                hybrid_hits = await hybrid.search(query, top_k=top_k)
                hits = [
                    {
                        "id": h.id,
                        "content": h.content,
                        "metadata": h.metadata,
                        "distance": 1.0 - float(h.score or 0.0),
                        "score_type": "rrf",
                    }
                    for h in hybrid_hits
                ]
            except Exception:
                hits = store.query(query, n_results=top_k)
        else:
            hits = store.query(query, n_results=top_k)

        results = []
        evidence_pack = []
        context_parts = []
        for hit in hits:
            content = hit.get("content", "")
            meta = hit.get("metadata", {}) or {}
            source = meta.get("filename", meta.get("source", "unknown"))
            distance = hit.get("distance")
            score = None
            if distance is not None:
                try:
                    score = round(1.0 - float(distance), 6)
                except (TypeError, ValueError):
                    score = None
            results.append(
                {
                    "id": hit.get("id"),
                    "content": content,
                    "metadata": meta,
                    "score": score,
                    "distance": distance,
                }
            )
            evidence_pack.append(
                {
                    "chunk_id": hit.get("id"),
                    "source": source,
                    "content_snippet": content,
                    "metadata": meta,
                }
            )
            context_parts.append(f"[{source}]: {content}")

        return {
            "query": query,
            "kb": kb,
            "top_k": top_k,
            "evidence_pack": evidence_pack,
            "results": results,
            "context": "\n\n".join(context_parts),
        }


class _LocalVectorAdapter(AsyncVectorStore):
    def __init__(self, store: VectorStore) -> None:
        self._store = store

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        hits = self._store.query(query, n_results=top_k, filter_dict=filters)
        results: List[SearchResult] = []
        for rank, hit in enumerate(hits):
            content = hit.get("content", "")
            meta = hit.get("metadata", {}) or {}
            distance = hit.get("distance")
            score = 0.0
            if distance is not None:
                try:
                    score = 1.0 - float(distance)
                except (TypeError, ValueError):
                    score = 0.0
            results.append(
                SearchResult(
                    id=str(hit.get("id")),
                    content=content,
                    score=score,
                    metadata=meta,
                    rank=rank,
                )
            )
        return results
