"""Knowledge Retriever — Dense retrieval + SelfRAG filter."""
from __future__ import annotations

import json
from typing import Any

import structlog

log = structlog.get_logger()


class KnowledgeRetriever:
    """
    Two-stage retrieval pipeline:
    1. Dense ANN search via pgvector (fast)
    2. SelfRAG self-consistency filter — LLM judges relevance of each candidate
    3. Cross-encoder reranking
    """

    def __init__(self, db: Any, gateway: Any) -> None:
        self.db = db
        self.gateway = gateway

    async def fast_retrieve(self, query: str) -> dict[str, Any] | None:
        """
        Hot Path Retrieval:
        - Embeds the query.
        - Performs a single dense search.
        - Returns the top result ONLY if score > 0.9.
        - Skips SelfRAG and Reranking for < 1s latency.
        """
        from salesagent.core.settings import settings
        embedding = await self._embed(query)
        candidates = await self._dense_search(embedding, top_k=1)

        if candidates and candidates[0].get("score", 0) > settings.hot_path_threshold:
            log.info("Hot Path match found", score=candidates[0]["score"])
            return candidates[0]

        return None

    async def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Full retrieval pipeline: dense → selfrag → rerank → top_k results."""
        # Step 1: Embed query
        embedding = await self._embed(query)

        # Step 2: Dense ANN search
        candidates = await self._dense_search(embedding, top_k=top_k * 3)
        if not candidates:
            return []

        # Step 3: SelfRAG filter
        relevant = await self._selfrag_filter(query, candidates)
        if not relevant:
            relevant = candidates[:top_k]  # fall back to raw ranking

        # Step 4: Rerank and return top_k
        from salesagent.knowledge.reranker import CrossEncoderReranker
        reranker = CrossEncoderReranker()
        reranked = await reranker.rerank(query, relevant)
        return reranked[:top_k]

    async def _embed(self, text: str) -> list[float]:
        """Generate embedding for query. Falls back to zero vector in mock mode."""
        from salesagent.core.settings import settings
        if settings.mock_llm:
            return [0.0] * settings.embedding_dimension

        try:
            import openai
            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.embeddings.create(
                model=settings.embedding_model,
                input=text,
            )
            return resp.data[0].embedding
        except Exception:
            return [0.0] * settings.embedding_dimension

    async def _dense_search(self, embedding: list[float], top_k: int) -> list[dict[str, Any]]:
        """pgvector cosine similarity search."""
        try:
            from sqlalchemy import text as sa_text
            vec_str = "[" + ",".join(str(x) for x in embedding) + "]"
            result = await self.db.execute(
                sa_text("""
                    SELECT id, document_name, content, metadata,
                           1 - (embedding <=> :embedding::vector) AS score
                    FROM knowledge_chunks
                    ORDER BY embedding <=> :embedding::vector
                    LIMIT :top_k
                """),
                {"embedding": vec_str, "top_k": top_k},
            )
            rows = result.mappings().all()
            return [dict(r) for r in rows]
        except Exception:
            return []

    async def _selfrag_filter(
        self, query: str, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """SelfRAG: ask the LLM if each chunk is actually relevant to the query."""
        from salesagent.reasoning.prompts import SELFRAG_FILTER_PROMPT

        relevant = []
        for chunk in candidates:
            try:
                prompt = SELFRAG_FILTER_PROMPT.format(
                    user_message=query,
                    chunk=chunk.get("content", "")[:500],
                )
                raw = await self.gateway.complete(
                    task="selfrag_filter",
                    system="You are a relevance judge. Be strict.",
                    user=prompt,
                )
                result = json.loads(raw)
                if result.get("relevant", False):
                    relevant.append(chunk)
            except Exception:
                relevant.append(chunk)  # on error, include candidate
        return relevant
