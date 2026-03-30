"""
BGE-M3 Dual-Path Retrieval (Dense + Sparse).

BGE-M3 is a powerful multilingual embedding model that natively supports:
1. Dense retrieval: Traditional semantic vector search
2. Sparse retrieval: Learned sparse vectors (similar to BM25 but learned)
3. Multi-vector retrieval: ColBERT-style token-level matching

This module implements the dual-path retrieval strategy using BGE-M3.

References:
- Paper: https://arxiv.org/abs/2402.03216
- Model: BAAI/bge-m3
- Dimensions: 1024 (dense), variable (sparse)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    from FlagEmbedding import BGEM3FlagModel
except ImportError:
    BGEM3FlagModel = None
    logger.warning("FlagEmbedding not available. Install with: pip install FlagEmbedding")


@dataclass
class BGEM3Embedding:
    """BGE-M3 embedding with dense and sparse vectors."""

    dense_vector: List[float]  # 1024-dim dense vector
    sparse_vector: Dict[int, float]  # Sparse vector (token_id -> weight)
    colbert_vector: Optional[List[List[float]]] = None  # Multi-vector (optional)


class BGEM3Encoder:
    """
    BGE-M3 encoder for dual-path retrieval.

    Features:
    - Dense vectors (1024-dim): Semantic similarity
    - Sparse vectors: Learned keyword matching
    - Multi-vector (optional): Token-level matching

    Args:
        model_name: Model name (default: BAAI/bge-m3)
        use_fp16: Use FP16 for faster inference (default: True)
        device: Device to use (default: cpu)
        batch_size: Batch size for encoding (default: 32)
    """

    _instance: Optional["BGEM3Encoder"] = None
    _model: Optional[Any] = None

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        use_fp16: bool = True,
        device: str = "cpu",
        batch_size: int = 32,
    ):
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self.device = device
        self.batch_size = batch_size
        self._load_model()

    def _load_model(self):
        """Load BGE-M3 model with caching."""
        if BGEM3Encoder._model is None:
            if BGEM3FlagModel is None:
                logger.error("FlagEmbedding not available. Cannot load BGE-M3.")
                return

            try:
                logger.info(f"Loading BGE-M3 model: {self.model_name}")
                BGEM3Encoder._model = BGEM3FlagModel(
                    self.model_name,
                    use_fp16=self.use_fp16,
                    device=self.device,
                )
                logger.info("BGE-M3 model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load BGE-M3 model: {e}")
                BGEM3Encoder._model = None

    @classmethod
    def get_instance(
        cls,
        model_name: str = "BAAI/bge-m3",
        use_fp16: bool = True,
        device: str = "cpu",
        batch_size: int = 32,
    ) -> "BGEM3Encoder":
        """Get singleton instance of BGE-M3 encoder."""
        if cls._instance is None:
            cls._instance = cls(model_name, use_fp16, device, batch_size)
        return cls._instance

    def encode(
        self,
        texts: List[str],
        return_dense: bool = True,
        return_sparse: bool = True,
        return_colbert: bool = False,
        max_length: int = 512,
    ) -> List[BGEM3Embedding]:
        """
        Encode texts using BGE-M3.

        Args:
            texts: List of texts to encode
            return_dense: Return dense vectors (default: True)
            return_sparse: Return sparse vectors (default: True)
            return_colbert: Return ColBERT vectors (default: False)
            max_length: Maximum sequence length (default: 512)

        Returns:
            List of BGEM3Embedding objects
        """
        if BGEM3Encoder._model is None:
            logger.error("BGE-M3 model not loaded")
            # Return dummy embeddings
            return [
                BGEM3Embedding(
                    dense_vector=[0.0] * 1024,
                    sparse_vector={},
                    colbert_vector=None,
                )
                for _ in texts
            ]

        try:
            # Encode with BGE-M3
            embeddings = BGEM3Encoder._model.encode(
                texts,
                batch_size=self.batch_size,
                max_length=max_length,
                return_dense=return_dense,
                return_sparse=return_sparse,
                return_colbert_vecs=return_colbert,
            )

            # Convert to BGEM3Embedding objects
            results = []
            for i in range(len(texts)):
                dense = embeddings["dense_vecs"][i].tolist() if return_dense else []
                sparse = embeddings["lexical_weights"][i] if return_sparse else {}
                colbert = (
                    embeddings["colbert_vecs"][i].tolist() if return_colbert else None
                )

                results.append(
                    BGEM3Embedding(
                        dense_vector=dense,
                        sparse_vector=sparse,
                        colbert_vector=colbert,
                    )
                )

            return results

        except Exception as e:
            logger.error(f"BGE-M3 encoding failed: {e}", exc_info=True)
            # Return dummy embeddings
            return [
                BGEM3Embedding(
                    dense_vector=[0.0] * 1024,
                    sparse_vector={},
                    colbert_vector=None,
                )
                for _ in texts
            ]

    def encode_single(
        self,
        text: str,
        return_dense: bool = True,
        return_sparse: bool = True,
        return_colbert: bool = False,
    ) -> BGEM3Embedding:
        """Encode a single text."""
        results = self.encode(
            [text],
            return_dense=return_dense,
            return_sparse=return_sparse,
            return_colbert=return_colbert,
        )
        return results[0]


class BGEM3DualPathRetriever:
    """
    Dual-path retriever using BGE-M3.

    Combines:
    1. Dense retrieval: Semantic similarity using 1024-dim vectors
    2. Sparse retrieval: Learned keyword matching using sparse vectors

    Fusion strategy: Weighted sum or RRF (Reciprocal Rank Fusion)

    Args:
        encoder: BGE-M3 encoder instance
        dense_weight: Weight for dense retrieval (default: 0.5)
        sparse_weight: Weight for sparse retrieval (default: 0.5)
        fusion_method: Fusion method ("weighted" or "rrf", default: "rrf")
        rrf_k: RRF k parameter (default: 60)
    """

    def __init__(
        self,
        encoder: Optional[BGEM3Encoder] = None,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
        fusion_method: str = "rrf",
        rrf_k: int = 60,
    ):
        self.encoder = encoder or BGEM3Encoder.get_instance()
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.fusion_method = fusion_method
        self.rrf_k = rrf_k

        # Validate weights
        if abs(dense_weight + sparse_weight - 1.0) > 0.01:
            logger.warning(
                f"Dense weight ({dense_weight}) + Sparse weight ({sparse_weight}) != 1.0. "
                "Normalizing weights."
            )
            total = dense_weight + sparse_weight
            self.dense_weight = dense_weight / total
            self.sparse_weight = sparse_weight / total

    def compute_dense_similarity(
        self,
        query_vector: List[float],
        doc_vectors: List[List[float]],
    ) -> List[float]:
        """
        Compute cosine similarity for dense vectors.

        Args:
            query_vector: Query dense vector (1024-dim)
            doc_vectors: List of document dense vectors

        Returns:
            List of similarity scores
        """
        query_np = np.array(query_vector)
        doc_np = np.array(doc_vectors)

        # Normalize
        query_norm = query_np / (np.linalg.norm(query_np) + 1e-8)
        doc_norm = doc_np / (np.linalg.norm(doc_np, axis=1, keepdims=True) + 1e-8)

        # Cosine similarity
        similarities = np.dot(doc_norm, query_norm)

        return similarities.tolist()

    def compute_sparse_similarity(
        self,
        query_sparse: Dict[int, float],
        doc_sparse_list: List[Dict[int, float]],
    ) -> List[float]:
        """
        Compute similarity for sparse vectors.

        Uses dot product of sparse vectors.

        Args:
            query_sparse: Query sparse vector
            doc_sparse_list: List of document sparse vectors

        Returns:
            List of similarity scores
        """
        scores = []

        for doc_sparse in doc_sparse_list:
            # Compute dot product
            score = 0.0
            for token_id, weight in query_sparse.items():
                if token_id in doc_sparse:
                    score += weight * doc_sparse[token_id]

            scores.append(score)

        return scores

    def fuse_scores(
        self,
        dense_scores: List[float],
        sparse_scores: List[float],
        doc_ids: List[str],
    ) -> List[Tuple[str, float]]:
        """
        Fuse dense and sparse scores.

        Args:
            dense_scores: Dense retrieval scores
            sparse_scores: Sparse retrieval scores
            doc_ids: Document IDs

        Returns:
            List of (doc_id, fused_score) tuples, sorted by score descending
        """
        if self.fusion_method == "weighted":
            # Weighted sum
            fused_scores = [
                self.dense_weight * d + self.sparse_weight * s
                for d, s in zip(dense_scores, sparse_scores)
            ]

            results = list(zip(doc_ids, fused_scores))
            results.sort(key=lambda x: x[1], reverse=True)

            return results

        elif self.fusion_method == "rrf":
            # RRF (Reciprocal Rank Fusion)
            # Sort by dense scores
            dense_ranked = sorted(
                enumerate(dense_scores), key=lambda x: x[1], reverse=True
            )
            dense_ranks = {idx: rank for rank, (idx, _) in enumerate(dense_ranked)}

            # Sort by sparse scores
            sparse_ranked = sorted(
                enumerate(sparse_scores), key=lambda x: x[1], reverse=True
            )
            sparse_ranks = {idx: rank for rank, (idx, _) in enumerate(sparse_ranked)}

            # Compute RRF scores
            rrf_scores = []
            for idx in range(len(doc_ids)):
                dense_rank = dense_ranks.get(idx, len(doc_ids))
                sparse_rank = sparse_ranks.get(idx, len(doc_ids))

                rrf_score = (1.0 / (self.rrf_k + dense_rank + 1)) + (
                    1.0 / (self.rrf_k + sparse_rank + 1)
                )
                rrf_scores.append(rrf_score)

            results = list(zip(doc_ids, rrf_scores))
            results.sort(key=lambda x: x[1], reverse=True)

            return results

        else:
            raise ValueError(f"Unknown fusion method: {self.fusion_method}")

    async def retrieve(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents using dual-path strategy.

        Args:
            query: Search query
            documents: List of documents with "id", "content", "dense_vector", "sparse_vector"
            top_k: Number of results to return

        Returns:
            List of retrieved documents with scores
        """
        # Encode query
        query_embedding = self.encoder.encode_single(
            query,
            return_dense=True,
            return_sparse=True,
            return_colbert=False,
        )

        # Extract document vectors
        doc_ids = [doc["id"] for doc in documents]
        doc_dense = [doc["dense_vector"] for doc in documents]
        doc_sparse = [doc["sparse_vector"] for doc in documents]

        # Compute dense similarities
        dense_scores = self.compute_dense_similarity(
            query_embedding.dense_vector, doc_dense
        )

        # Compute sparse similarities
        sparse_scores = self.compute_sparse_similarity(
            query_embedding.sparse_vector, doc_sparse
        )

        # Fuse scores
        fused_results = self.fuse_scores(dense_scores, sparse_scores, doc_ids)

        # Return top-k
        top_results = fused_results[:top_k]

        # Build result documents
        doc_map = {doc["id"]: doc for doc in documents}
        results = []

        for doc_id, score in top_results:
            doc = doc_map[doc_id].copy()
            doc["score"] = score
            results.append(doc)

        logger.info(
            f"Retrieved {len(results)} documents using BGE-M3 dual-path "
            f"(fusion: {self.fusion_method})"
        )

        return results
