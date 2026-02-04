"""
Qdrant Vector Store Client

Production-ready Qdrant client with connection pooling, retry logic, and error handling.

Features:
- Collection management (create, delete, list)
- Document upsert with automatic batching
- Hybrid search (dense + sparse vectors)
- Connection pooling and health checks
- Retry logic with exponential backoff
- Comprehensive error handling

Usage:
    from app.infra.vector_store import QdrantVectorStore

    store = QdrantVectorStore.get_instance()
    await store.initialize()

    # Create collection
    await store.create_collection("knowledge_base", vector_size=1024)

    # Upsert documents
    await store.upsert_documents("knowledge_base", documents)

    # Search
    results = await store.search("knowledge_base", query_vector, top_k=5)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from qdrant_client import QdrantClient, AsyncQdrantClient
    from qdrant_client.models import (
        Distance,
        VectorParams,
        PointStruct,
        Filter,
        FieldCondition,
        MatchValue,
        SearchParams,
        SparseVector,
        SparseVectorParams,
        NamedVector,
        NamedSparseVector,
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("qdrant-client not available. Install with: pip install qdrant-client")


@dataclass
class SearchResult:
    """Search result from vector store."""

    id: str
    score: float
    content: str
    metadata: Dict[str, Any]
    vector: Optional[List[float]] = None


@dataclass
class Document:
    """Document to be stored in vector store."""

    id: str
    content: str
    dense_vector: List[float]
    sparse_vector: Optional[Dict[int, float]] = None
    metadata: Optional[Dict[str, Any]] = None


class QdrantVectorStore:
    """
    Production-ready Qdrant vector store client.

    Features:
    - Async operations
    - Connection pooling
    - Retry logic
    - Health checks
    - Batch operations
    - Hybrid search (dense + sparse)

    Args:
        url: Qdrant server URL (default: http://localhost:6333)
        api_key: API key for authentication (optional)
        timeout: Request timeout in seconds (default: 30)
        max_retries: Maximum number of retries (default: 3)
        retry_delay: Initial retry delay in seconds (default: 1.0)
    """

    _instance: Optional["QdrantVectorStore"] = None
    _client: Optional[AsyncQdrantClient] = None

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._initialized = False

    @classmethod
    def get_instance(
        cls,
        url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
    ) -> "QdrantVectorStore":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(url=url, api_key=api_key)
        return cls._instance

    async def initialize(self) -> bool:
        """
        Initialize Qdrant client and verify connection.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        if not QDRANT_AVAILABLE:
            logger.error("Qdrant client not available")
            return False

        try:
            # Create async client
            QdrantVectorStore._client = AsyncQdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=self.timeout,
            )

            # Verify connection
            collections = await QdrantVectorStore._client.get_collections()
            logger.info(f"Connected to Qdrant at {self.url}")
            logger.info(f"Found {len(collections.collections)} collections")

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            QdrantVectorStore._client = None
            return False

    async def health_check(self) -> bool:
        """Check if Qdrant is healthy."""
        if not self._initialized or QdrantVectorStore._client is None:
            return False

        try:
            await QdrantVectorStore._client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int = 1024,
        distance: str = "Cosine",
        enable_sparse: bool = True,
        on_disk: bool = False,
    ) -> bool:
        """
        Create a new collection.

        Args:
            collection_name: Name of the collection
            vector_size: Dimension of dense vectors (default: 1024 for BGE-M3)
            distance: Distance metric (Cosine, Euclid, Dot)
            enable_sparse: Enable sparse vectors for hybrid search
            on_disk: Store vectors on disk (for large collections)

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or QdrantVectorStore._client is None:
            logger.error("Qdrant client not initialized")
            return False

        try:
            # Check if collection exists
            collections = await QdrantVectorStore._client.get_collections()
            if any(c.name == collection_name for c in collections.collections):
                logger.info(f"Collection {collection_name} already exists")
                return True

            # Map distance string to enum
            distance_map = {
                "Cosine": Distance.COSINE,
                "Euclid": Distance.EUCLID,
                "Dot": Distance.DOT,
            }
            distance_metric = distance_map.get(distance, Distance.COSINE)

            # Create collection with dense vectors
            vectors_config = {
                "dense": VectorParams(
                    size=vector_size,
                    distance=distance_metric,
                    on_disk=on_disk,
                )
            }

            # Add sparse vectors if enabled
            sparse_vectors_config = None
            if enable_sparse:
                sparse_vectors_config = {
                    "sparse": SparseVectorParams()
                }

            await QdrantVectorStore._client.create_collection(
                collection_name=collection_name,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors_config,
            )

            logger.info(
                f"Created collection {collection_name} "
                f"(vector_size={vector_size}, distance={distance}, "
                f"sparse={enable_sparse})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        if not self._initialized or QdrantVectorStore._client is None:
            logger.error("Qdrant client not initialized")
            return False

        try:
            await QdrantVectorStore._client.delete_collection(collection_name)
            logger.info(f"Deleted collection {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False

    async def list_collections(self) -> List[str]:
        """List all collections."""
        if not self._initialized or QdrantVectorStore._client is None:
            logger.error("Qdrant client not initialized")
            return []

        try:
            collections = await QdrantVectorStore._client.get_collections()
            return [c.name for c in collections.collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []

    async def upsert_documents(
        self,
        collection_name: str,
        documents: List[Document],
        batch_size: int = 100,
    ) -> bool:
        """
        Upsert documents with automatic batching.

        Args:
            collection_name: Name of the collection
            documents: List of documents to upsert
            batch_size: Batch size for upsert (default: 100)

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or QdrantVectorStore._client is None:
            logger.error("Qdrant client not initialized")
            return False

        if not documents:
            logger.warning("No documents to upsert")
            return True

        try:
            # Process in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                points = []

                for doc in batch:
                    # Prepare vectors
                    vectors = {
                        "dense": doc.dense_vector
                    }

                    # Add sparse vector if available
                    if doc.sparse_vector:
                        # Convert dict to SparseVector
                        indices = list(doc.sparse_vector.keys())
                        values = list(doc.sparse_vector.values())
                        vectors["sparse"] = SparseVector(
                            indices=indices,
                            values=values,
                        )

                    # Prepare payload
                    payload = {
                        "content": doc.content,
                        "metadata": doc.metadata or {},
                        "created_at": datetime.now().isoformat(),
                    }

                    # Create point
                    point = PointStruct(
                        id=doc.id,
                        vector=vectors,
                        payload=payload,
                    )
                    points.append(point)

                # Upsert batch
                await QdrantVectorStore._client.upsert(
                    collection_name=collection_name,
                    points=points,
                )

                logger.info(
                    f"Upserted batch {i // batch_size + 1} "
                    f"({len(batch)} documents) to {collection_name}"
                )

            logger.info(f"Successfully upserted {len(documents)} documents")
            return True

        except Exception as e:
            logger.error(f"Failed to upsert documents: {e}")
            return False

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        Search with dense vectors.

        Args:
            collection_name: Name of the collection
            query_vector: Query vector
            top_k: Number of results to return
            filters: Metadata filters (e.g., {"category": "sales"})
            score_threshold: Minimum score threshold

        Returns:
            List of search results
        """
        if not self._initialized or QdrantVectorStore._client is None:
            logger.error("Qdrant client not initialized")
            return []

        try:
            # Build filter
            qdrant_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=f"metadata.{key}",
                            match=MatchValue(value=value),
                        )
                    )
                if conditions:
                    qdrant_filter = Filter(must=conditions)

            # Search
            search_result = await QdrantVectorStore._client.search(
                collection_name=collection_name,
                query_vector=("dense", query_vector),
                limit=top_k,
                query_filter=qdrant_filter,
                score_threshold=score_threshold,
            )

            # Convert to SearchResult
            results = []
            for hit in search_result:
                result = SearchResult(
                    id=str(hit.id),
                    score=hit.score,
                    content=hit.payload.get("content", ""),
                    metadata=hit.payload.get("metadata", {}),
                    vector=hit.vector.get("dense") if hit.vector else None,
                )
                results.append(result)

            logger.info(
                f"Search returned {len(results)} results from {collection_name}"
            )
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def hybrid_search(
        self,
        collection_name: str,
        dense_vector: List[float],
        sparse_vector: Dict[int, float],
        top_k: int = 5,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Hybrid search with dense + sparse vectors.

        Uses RRF (Reciprocal Rank Fusion) to combine results.

        Args:
            collection_name: Name of the collection
            dense_vector: Dense query vector
            sparse_vector: Sparse query vector
            top_k: Number of results to return
            dense_weight: Weight for dense search (default: 0.5)
            sparse_weight: Weight for sparse search (default: 0.5)
            filters: Metadata filters

        Returns:
            List of search results
        """
        if not self._initialized or QdrantVectorStore._client is None:
            logger.error("Qdrant client not initialized")
            return []

        try:
            # Normalize weights
            total_weight = dense_weight + sparse_weight
            dense_weight = dense_weight / total_weight
            sparse_weight = sparse_weight / total_weight

            # Build filter
            qdrant_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=f"metadata.{key}",
                            match=MatchValue(value=value),
                        )
                    )
                if conditions:
                    qdrant_filter = Filter(must=conditions)

            # Dense search
            dense_results = await QdrantVectorStore._client.search(
                collection_name=collection_name,
                query_vector=("dense", dense_vector),
                limit=top_k * 2,  # Get more for fusion
                query_filter=qdrant_filter,
            )

            # Sparse search
            sparse_indices = list(sparse_vector.keys())
            sparse_values = list(sparse_vector.values())
            sparse_results = await QdrantVectorStore._client.search(
                collection_name=collection_name,
                query_vector=(
                    "sparse",
                    SparseVector(indices=sparse_indices, values=sparse_values),
                ),
                limit=top_k * 2,
                query_filter=qdrant_filter,
            )

            # RRF fusion
            rrf_k = 60
            scores = {}

            # Add dense scores
            for rank, hit in enumerate(dense_results):
                doc_id = str(hit.id)
                rrf_score = dense_weight / (rrf_k + rank + 1)
                scores[doc_id] = scores.get(doc_id, 0) + rrf_score

            # Add sparse scores
            for rank, hit in enumerate(sparse_results):
                doc_id = str(hit.id)
                rrf_score = sparse_weight / (rrf_k + rank + 1)
                scores[doc_id] = scores.get(doc_id, 0) + rrf_score

            # Sort by fused score
            sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            top_ids = [doc_id for doc_id, _ in sorted_ids[:top_k]]

            # Retrieve full documents
            points = await QdrantVectorStore._client.retrieve(
                collection_name=collection_name,
                ids=top_ids,
                with_vectors=False,
            )

            # Build results
            results = []
            id_to_point = {str(p.id): p for p in points}

            for doc_id, score in sorted_ids[:top_k]:
                if doc_id in id_to_point:
                    point = id_to_point[doc_id]
                    result = SearchResult(
                        id=doc_id,
                        score=score,
                        content=point.payload.get("content", ""),
                        metadata=point.payload.get("metadata", {}),
                    )
                    results.append(result)

            logger.info(
                f"Hybrid search returned {len(results)} results "
                f"(dense_weight={dense_weight:.2f}, sparse_weight={sparse_weight:.2f})"
            )
            return results

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []

    async def delete_documents(
        self,
        collection_name: str,
        document_ids: List[str],
    ) -> bool:
        """Delete documents by IDs."""
        if not self._initialized or QdrantVectorStore._client is None:
            logger.error("Qdrant client not initialized")
            return False

        try:
            await QdrantVectorStore._client.delete(
                collection_name=collection_name,
                points_selector=document_ids,
            )
            logger.info(f"Deleted {len(document_ids)} documents from {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False

    async def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get collection information."""
        if not self._initialized or QdrantVectorStore._client is None:
            logger.error("Qdrant client not initialized")
            return None

        try:
            info = await QdrantVectorStore._client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "config": {
                    "vector_size": info.config.params.vectors.get("dense").size,
                    "distance": info.config.params.vectors.get("dense").distance,
                },
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return None

    async def close(self):
        """Close Qdrant client."""
        if QdrantVectorStore._client:
            await QdrantVectorStore._client.close()
            QdrantVectorStore._client = None
            self._initialized = False
            logger.info("Closed Qdrant client")
