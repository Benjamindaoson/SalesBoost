"""Cross-encoder reranker for knowledge retrieval."""
from __future__ import annotations

from typing import Any

import structlog

log = structlog.get_logger()


class CrossEncoderReranker:
    """
    Reranks retrieved knowledge chunks using a cross-encoder model.
    Falls back to score-sort if the model is unavailable.
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._loaded = False

    def _load_model(self) -> None:
        if not self._loaded:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
                self._loaded = True
            except Exception:
                self._loaded = True  # mark as attempted, fallback to score-sort

    async def rerank(self, query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rerank chunks by cross-encoder score. Falls back to existing score order."""
        if not chunks:
            return chunks

        self._load_model()

        if self._model is None:
            # Fallback: sort by existing vector score
            return sorted(chunks, key=lambda x: float(x.get("score", 0.0)), reverse=True)

        try:
            import asyncio
            pairs = [(query, c.get("content", "")[:512]) for c in chunks]
            scores = await asyncio.to_thread(self._model.predict, pairs)
            for chunk, score in zip(chunks, scores):
                chunk["rerank_score"] = float(score)
            return sorted(chunks, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        except Exception as exc:
            log.warning("Reranker failed, falling back to score sort", error=str(exc))
            return sorted(chunks, key=lambda x: float(x.get("score", 0.0)), reverse=True)
