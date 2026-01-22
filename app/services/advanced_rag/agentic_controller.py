from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.advanced_rag.retrieval_quality import compute_quality, should_retry

logger = logging.getLogger(__name__)


class AgenticController:
    """
    Agentic RAG 控制器：
    - Self-Querying: 检索质量不足时自动改写/扩展查询
    - Corrective RAG: 评分不足触发二次检索
    """

    def __init__(self, base_retriever):
        self.base_retriever = base_retriever

    async def search(
        self,
        query: str,
        top_k: int,
        filter_meta: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        results = await self._base_search(query, top_k, filter_meta, context)
        quality, stats = compute_quality(query, results)

        if should_retry(quality, stats):
            logger.info(
                "Agentic retrieval retry triggered: quality=%.2f coverage=%.2f",
                quality,
                stats.get("coverage", 0.0),
            )
            expanded = await self._expand_queries(query, context)
            fused = await self._multi_query_search(expanded, top_k, filter_meta, context)
            if fused:
                results = fused
        return results

    async def _base_search(
        self,
        query: str,
        top_k: int,
        filter_meta: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return await self.base_retriever.search(
            query=query,
            top_k=top_k,
            filter_meta=filter_meta,
            use_rag_fusion=False,
            context=context,
            use_adaptive=False,
            use_agentic=False,
        )

    async def _expand_queries(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
    ) -> List[str]:
        if self.base_retriever.query_expander:
            try:
                return await self.base_retriever.query_expander.expand_query(
                    original_query=query,
                    context=context or {},
                    num_variants=4,
                )
            except Exception as exc:
                logger.warning("Query expansion failed: %s", exc)
        return [query]

    async def _multi_query_search(
        self,
        queries: List[str],
        top_k: int,
        filter_meta: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        aggregated: List[Dict[str, Any]] = []
        for q in queries:
            if not q:
                continue
            results = await self._base_search(q, top_k, filter_meta, context)
            aggregated.extend(results or [])
        return self._rrf_fuse(aggregated, top_k=top_k)

    def _rrf_fuse(self, results: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        if not results:
            return []
        scores: Dict[str, float] = {}
        metadata: Dict[str, Dict[str, Any]] = {}
        for rank, result in enumerate(results, start=1):
            content = result.get("content", "")
            if not content:
                continue
            scores[content] = scores.get(content, 0.0) + 1.0 / (rank + 60)
            metadata[content] = result.get("metadata", {})

        fused = [
            {
                "content": content,
                "metadata": metadata.get(content, {}),
                "rerank_score": score,
                "rank": idx + 1,
                "source": "agentic_rrf",
            }
            for idx, (content, score) in enumerate(sorted(scores.items(), key=lambda x: x[1], reverse=True))
        ]
        return fused[:top_k]
