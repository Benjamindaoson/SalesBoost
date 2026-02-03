"""
BGE-M3 Embedding Service

BGE-M3 is a state-of-the-art multilingual embedding model that supports:
- Dense embeddings (semantic similarity)
- Sparse embeddings (keyword matching)
- Multi-vector embeddings (ColBERT-style)

This provides superior retrieval accuracy, especially for Chinese text.

Architecture:
    Text → BGE-M3 → {dense, sparse, colbert} → Hybrid Search

Usage:
    from app.agents.study.bge_m3_embedder import BGEM3Embedder

    embedder = BGEM3Embedder()
    result = embedder.embed(["你好世界", "Hello world"])
    # Returns: {"dense": [...], "sparse": {...}, "colbert": [...]}
"""

import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)


class BGEM3Embedder:
    """
    BGE-M3 embedding service with hybrid retrieval support

    Features:
    - Dense embeddings (768-dim) for semantic search
    - Sparse embeddings (BM25-style) for keyword matching
    - ColBERT multi-vector for fine-grained matching
    - Automatic batching for efficiency
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        use_fp16: bool = True,
        device: Optional[str] = None,
        batch_size: int = 32,
        max_length: int = 512,
    ):
        """
        Initialize BGE-M3 embedder

        Args:
            model_name: Model name from HuggingFace
            use_fp16: Use FP16 for faster inference
            device: Device to use (cuda/cpu, auto-detected if None)
            batch_size: Batch size for encoding
            max_length: Maximum sequence length
        """
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self.batch_size = batch_size
        self.max_length = max_length

        # Lazy import to avoid dependency issues
        try:
            from FlagEmbedding import BGEM3FlagModel
        except ImportError:
            raise ImportError(
                "FlagEmbedding not installed. Install with: "
                "pip install FlagEmbedding"
            )

        # Auto-detect device
        if device is None:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device

        logger.info(f"[BGEM3Embedder] Loading model: {model_name} on {device}")

        # Load model
        self.model = BGEM3FlagModel(
            model_name,
            use_fp16=use_fp16 and device == "cuda",
            device=device
        )

        logger.info(f"[BGEM3Embedder] Model loaded successfully")

    def embed(
        self,
        texts: Union[str, List[str]],
        return_dense: bool = True,
        return_sparse: bool = True,
        return_colbert: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate embeddings for texts

        Args:
            texts: Single text or list of texts
            return_dense: Return dense embeddings (768-dim)
            return_sparse: Return sparse embeddings (BM25-style)
            return_colbert: Return ColBERT multi-vectors

        Returns:
            {
                "dense": np.ndarray,  # Shape: (n, 768)
                "sparse": List[Dict[int, float]],  # Token weights
                "colbert": np.ndarray,  # Shape: (n, max_len, 768)
            }
        """
        # Normalize input
        if isinstance(texts, str):
            texts = [texts]

        logger.debug(f"[BGEM3Embedder] Embedding {len(texts)} texts")

        # Encode
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            max_length=self.max_length,
            return_dense=return_dense,
            return_sparse=return_sparse,
            return_colbert_vecs=return_colbert,
        )

        result = {}

        if return_dense:
            result["dense"] = embeddings["dense_vecs"]

        if return_sparse:
            result["sparse"] = embeddings["lexical_weights"]

        if return_colbert:
            result["colbert"] = embeddings["colbert_vecs"]

        logger.debug(
            f"[BGEM3Embedder] Generated embeddings: "
            f"dense={return_dense}, sparse={return_sparse}, colbert={return_colbert}"
        )

        return result

    def embed_query(self, query: str) -> Dict[str, Any]:
        """
        Embed query for retrieval

        Args:
            query: Query text

        Returns:
            Embeddings dict
        """
        return self.embed(
            query,
            return_dense=True,
            return_sparse=True,
            return_colbert=False,
        )

    def embed_documents(
        self,
        documents: List[str],
        show_progress: bool = False
    ) -> Dict[str, Any]:
        """
        Embed documents for indexing

        Args:
            documents: List of document texts
            show_progress: Show progress bar

        Returns:
            Embeddings dict
        """
        if show_progress:
            from tqdm import tqdm
            batches = [
                documents[i:i + self.batch_size]
                for i in range(0, len(documents), self.batch_size)
            ]

            all_dense = []
            all_sparse = []

            for batch in tqdm(batches, desc="Embedding documents"):
                result = self.embed(
                    batch,
                    return_dense=True,
                    return_sparse=True,
                    return_colbert=False,
                )
                all_dense.append(result["dense"])
                all_sparse.extend(result["sparse"])

            return {
                "dense": np.vstack(all_dense),
                "sparse": all_sparse,
            }
        else:
            return self.embed(
                documents,
                return_dense=True,
                return_sparse=True,
                return_colbert=False,
            )

    def compute_similarity(
        self,
        query_embedding: Dict[str, Any],
        doc_embeddings: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None,
    ) -> np.ndarray:
        """
        Compute hybrid similarity scores

        Args:
            query_embedding: Query embeddings
            doc_embeddings: Document embeddings
            weights: Weights for each embedding type
                     {"dense": 0.5, "sparse": 0.5}

        Returns:
            Similarity scores (n_docs,)
        """
        if weights is None:
            weights = {"dense": 0.5, "sparse": 0.5}

        scores = np.zeros(len(doc_embeddings["dense"]))

        # Dense similarity (cosine)
        if "dense" in query_embedding and "dense" in doc_embeddings:
            query_dense = query_embedding["dense"]
            doc_dense = doc_embeddings["dense"]

            # Normalize
            query_norm = query_dense / np.linalg.norm(query_dense)
            doc_norm = doc_dense / np.linalg.norm(doc_dense, axis=1, keepdims=True)

            # Cosine similarity
            dense_scores = np.dot(doc_norm, query_norm)
            scores += weights.get("dense", 0.5) * dense_scores

        # Sparse similarity (BM25-style)
        if "sparse" in query_embedding and "sparse" in doc_embeddings:
            query_sparse = query_embedding["sparse"][0]  # Dict[int, float]
            doc_sparse = doc_embeddings["sparse"]  # List[Dict[int, float]]

            sparse_scores = []
            for doc_weights in doc_sparse:
                score = sum(
                    query_sparse.get(token, 0) * doc_weights.get(token, 0)
                    for token in set(query_sparse.keys()) | set(doc_weights.keys())
                )
                sparse_scores.append(score)

            scores += weights.get("sparse", 0.5) * np.array(sparse_scores)

        return scores


# ==================== Integration with Qdrant ====================

class BGEM3QdrantStore:
    """
    Qdrant vector store with BGE-M3 hybrid search

    Stores both dense and sparse vectors for hybrid retrieval.
    """

    def __init__(
        self,
        embedder: BGEM3Embedder,
        collection_name: str = "salesboost_bge_m3",
        qdrant_url: str = "http://localhost:6333",
        qdrant_api_key: Optional[str] = None,
    ):
        """
        Initialize BGE-M3 Qdrant store

        Args:
            embedder: BGE-M3 embedder instance
            collection_name: Qdrant collection name
            qdrant_url: Qdrant server URL
            qdrant_api_key: Qdrant API key (optional)
        """
        self.embedder = embedder
        self.collection_name = collection_name

        # Lazy import
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, SparseVectorParams
        except ImportError:
            raise ImportError(
                "qdrant-client not installed. Install with: "
                "pip install qdrant-client"
            )

        # Initialize client
        self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

        # Create collection if not exists
        try:
            self.client.get_collection(collection_name)
            logger.info(f"[BGEM3QdrantStore] Using existing collection: {collection_name}")
        except Exception:
            logger.info(f"[BGEM3QdrantStore] Creating collection: {collection_name}")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "dense": VectorParams(
                        size=768,
                        distance=Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams()
                },
            )

    async def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add documents to vector store

        Args:
            texts: Document texts
            metadatas: Document metadata
            ids: Document IDs (auto-generated if None)

        Returns:
            List of document IDs
        """
        import uuid

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]

        if metadatas is None:
            metadatas = [{} for _ in texts]

        # Generate embeddings
        embeddings = self.embedder.embed_documents(texts, show_progress=True)

        # Prepare points
        from qdrant_client.models import PointStruct, SparseVector

        points = []
        for i, (text, metadata, doc_id) in enumerate(zip(texts, metadatas, ids)):
            dense_vec = embeddings["dense"][i].tolist()
            sparse_dict = embeddings["sparse"][i]

            # Convert sparse dict to Qdrant format
            sparse_indices = list(sparse_dict.keys())
            sparse_values = [sparse_dict[idx] for idx in sparse_indices]

            point = PointStruct(
                id=doc_id,
                vector={
                    "dense": dense_vec,
                    "sparse": SparseVector(
                        indices=sparse_indices,
                        values=sparse_values,
                    ),
                },
                payload={
                    "text": text,
                    **metadata,
                },
            )
            points.append(point)

        # Upload to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        logger.info(f"[BGEM3QdrantStore] Added {len(points)} documents")

        return ids

    async def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid similarity search

        Args:
            query: Query text
            top_k: Number of results
            filter_dict: Metadata filters
            dense_weight: Weight for dense search
            sparse_weight: Weight for sparse search

        Returns:
            List of results with scores
        """
        # Generate query embeddings
        query_emb = self.embedder.embed_query(query)

        # Prepare query vectors
        from qdrant_client.models import SparseVector, NamedVector, Prefetch

        dense_vec = query_emb["dense"][0].tolist()
        sparse_dict = query_emb["sparse"][0]

        sparse_indices = list(sparse_dict.keys())
        sparse_values = [sparse_dict[idx] for idx in sparse_indices]

        # Hybrid search using prefetch
        results = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                Prefetch(
                    query=dense_vec,
                    using="dense",
                    limit=top_k * 2,
                ),
                Prefetch(
                    query=SparseVector(
                        indices=sparse_indices,
                        values=sparse_values,
                    ),
                    using="sparse",
                    limit=top_k * 2,
                ),
            ],
            query=NamedVector(
                name="dense",
                vector=dense_vec,
            ),
            limit=top_k,
        )

        # Format results
        formatted_results = []
        for result in results.points:
            formatted_results.append({
                "id": result.id,
                "text": result.payload.get("text", ""),
                "score": result.score,
                "metadata": {
                    k: v for k, v in result.payload.items()
                    if k != "text"
                },
            })

        logger.info(f"[BGEM3QdrantStore] Found {len(formatted_results)} results")

        return formatted_results


# ==================== Factory Functions ====================

_embedder_instance: Optional[BGEM3Embedder] = None


def get_bge_m3_embedder(force_new: bool = False) -> BGEM3Embedder:
    """
    Get or create BGE-M3 embedder instance (singleton)

    Args:
        force_new: Force create new instance

    Returns:
        BGEM3Embedder instance
    """
    global _embedder_instance

    if _embedder_instance is None or force_new:
        _embedder_instance = BGEM3Embedder()

    return _embedder_instance


def get_bge_m3_store(
    collection_name: str = "salesboost_bge_m3",
    force_new: bool = False
) -> BGEM3QdrantStore:
    """
    Get or create BGE-M3 Qdrant store

    Args:
        collection_name: Collection name
        force_new: Force create new instance

    Returns:
        BGEM3QdrantStore instance
    """
    from core.config import get_settings
    settings = get_settings()

    embedder = get_bge_m3_embedder(force_new=force_new)

    qdrant_url = getattr(settings, "QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = getattr(settings, "QDRANT_API_KEY", None)

    return BGEM3QdrantStore(
        embedder=embedder,
        collection_name=collection_name,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
    )
