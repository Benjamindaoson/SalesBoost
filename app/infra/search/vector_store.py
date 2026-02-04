import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from pydantic import BaseModel

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import (
        Distance,
        Filter,
        FieldCondition,
        MatchAny,
        MatchValue,
        PointStruct,
        VectorParams,
        HasIdCondition,
        PointIdsList,
    )
except Exception:  # pragma: no cover
    AsyncQdrantClient = None  # type: ignore
    Distance = Filter = FieldCondition = MatchAny = MatchValue = PointStruct = VectorParams = HasIdCondition = PointIdsList = None  # type: ignore

try:
    from FlagEmbedding import FlagReranker
except ImportError:  # pragma: no cover
    FlagReranker = None  # type: ignore

logger = logging.getLogger(__name__)

class SearchResult(BaseModel):
    id: str
    content: str
    score: float = 0.0
    metadata: Dict[str, Any] = {}
    rank: int = 0

class VectorStore:
    """
    Abstract Vector Store interface.
    """
    async def search(self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        raise NotImplementedError

class VectorStoreAdapter(VectorStore):
    """
    Qdrant-backed VectorStore adapter (async).
    Now with automatic embedding dimension detection and model management.
    """
    def __init__(
        self,
        collection_name: str,
        vector_size: Optional[int] = None,
        distance: str = "Cosine",
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> None:
        if AsyncQdrantClient is None:
            raise RuntimeError("qdrant-client is not available")

        from app.infra.search.embedding_manager import get_embedding_manager

        self.collection_name = collection_name
        self.distance = distance
        self._client = AsyncQdrantClient(url=url, api_key=api_key)
        self._init_done = False

        # Initialize embedding manager
        self._embedding_manager = get_embedding_manager(model_name=embedding_model)

        # Auto-detect vector size from embedding model
        if vector_size is None:
            self.vector_size = self._embedding_manager.get_dimension()
            logger.info(f"Auto-detected vector size: {self.vector_size}")
        else:
            self.vector_size = vector_size

        # Validate vector size matches model
        model_dim = self._embedding_manager.get_dimension()
        if self.vector_size != model_dim:
            logger.warning(
                f"Vector size {self.vector_size} does not match model dimension {model_dim}. "
                f"Using model dimension {model_dim}"
            )
            self.vector_size = model_dim

    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add documents to vector store using embedding manager."""
        if not ids:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]
        if not metadatas:
            metadatas = [{} for _ in documents]

        # Generate embeddings using embedding manager
        embeddings = await self._embedding_manager.encode_async(documents)

        await self.upsert(ids=ids, vectors=embeddings, payloads=metadatas)
        return ids

    async def _ensure_collection(self) -> None:
        if self._init_done:
            return
        try:
            existing = await self._client.get_collections()
            names = {c.name for c in existing.collections}
            if self.collection_name not in names:
                await self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )
            self._init_done = True
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to ensure Qdrant collection %s: %s", self.collection_name, exc)
            raise

    def _build_filter(
        self,
        filters: Optional[Dict[str, Any]] = None,
        ids: Optional[Iterable[str]] = None,
    ) -> Optional[Filter]:
        conditions = []
        if filters:
            for key, value in filters.items():
                if value is None:
                    continue
                if isinstance(value, (list, tuple, set)):
                    conditions.append(FieldCondition(key=key, match=MatchAny(any=list(value))))
                else:
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        if ids:
            conditions.append(HasIdCondition(has_id=list(ids)))
        if not conditions:
            return None
        return Filter(must=conditions)

    async def upsert(
        self,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> None:
        await self._ensure_collection()
        points = [PointStruct(id=pid, vector=vec, payload=payload) for pid, vec, payload in zip(ids, vectors, payloads)]
        await self._client.upsert(collection_name=self.collection_name, points=points)

    async def delete(self, ids: List[str]) -> None:
        """Delete vectors by ID."""
        await self._ensure_collection()
        await self._client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=ids),
        )

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count vectors matching filters."""
        await self._ensure_collection()
        query_filter = self._build_filter(filters)
        result = await self._client.count(
            collection_name=self.collection_name,
            count_filter=query_filter,
        )
        return result.count

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get collection statistics."""
        await self._ensure_collection()
        info = await self._client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "status": info.status,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "segments_count": info.segments_count,
            "config": info.config.dict() if hasattr(info.config, "dict") else info.config,
        }

    async def list_collections(self) -> List[str]:
        """List all collections."""
        if not self._client:
             return []
        result = await self._client.get_collections()
        return [c.name for c in result.collections]

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        try:
            await self._client.delete_collection(collection_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        ids: Optional[Iterable[str]] = None,
        embedding_fn: Optional[Callable[[str], Awaitable[List[float]]]] = None,
    ) -> List[SearchResult]:
        await self._ensure_collection()
        if embedding_fn is None:
            raise RuntimeError("embedding_fn is required for Qdrant search")
        vector = await embedding_fn(query)
        query_filter = self._build_filter(filters, ids)
        results = await self._client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            query_filter=query_filter,
            limit=top_k,
        )
        hits: List[SearchResult] = []
        for rank, res in enumerate(results):
            payload = res.payload or {}
            content = payload.get("content", "")
            hits.append(
                SearchResult(
                    id=str(res.id),
                    content=content,
                    score=float(res.score),
                    metadata={k: v for k, v in payload.items() if k != "content"},
                    rank=rank,
                )
            )
        return hits

class BM25Retriever(VectorStore):
    """
    BM25 Retriever - now implemented with real BM25 algorithm.

    For full implementation, see app.infra.search.bm25_retriever.
    This is a lightweight wrapper for backward compatibility.
    """
    def __init__(self, documents: Optional[List[Dict[str, Any]]] = None):
        from app.infra.search.bm25_retriever import BM25Retriever as RealBM25
        self._retriever = RealBM25(documents=documents)

    async def search(self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        return await self._retriever.search(query, top_k, filters)

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        self._retriever.index_documents(documents)

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        self._retriever.add_documents(documents)


class BGEReranker:
    """
    BGE-Reranker for improving search result ranking quality.

    Uses BAAI/bge-reranker models for cross-encoder reranking.
    Provides better ranking than simple vector similarity.
    """

    _instance: Optional["BGEReranker"] = None
    _model: Optional[Any] = None

    def __init__(self, model_name: str = "BAAI/bge-reranker-base", batch_size: int = 32):
        """
        Initialize BGE Reranker.

        Args:
            model_name: BGE reranker model name (base or large)
            batch_size: Batch size for reranking
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self._load_model()

    def _load_model(self):
        """Load BGE reranker model with caching."""
        if BGEReranker._model is None:
            if FlagReranker is None:
                logger.warning("FlagEmbedding not available, BGE reranker disabled")
                return
            try:
                logger.info(f"Loading BGE reranker model: {self.model_name}")
                BGEReranker._model = FlagReranker(self.model_name, use_fp16=True)
                logger.info("BGE reranker model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load BGE reranker: {e}")
                BGEReranker._model = None

    @classmethod
    def get_instance(cls, model_name: str = "BAAI/bge-reranker-base", batch_size: int = 32) -> "BGEReranker":
        """Get singleton instance of BGE reranker."""
        if cls._instance is None:
            cls._instance = cls(model_name, batch_size)
        return cls._instance

    def rerank(self, query: str, results: List[SearchResult], top_k: Optional[int] = None) -> List[SearchResult]:
        """
        Rerank search results using BGE cross-encoder.

        Args:
            query: Search query
            results: List of search results to rerank
            top_k: Number of top results to return (None = all)

        Returns:
            Reranked list of search results
        """
        if not results:
            return results

        if BGEReranker._model is None:
            logger.warning("BGE reranker not available, returning original results")
            return results

        try:
            # Prepare query-document pairs
            pairs = [[query, result.content] for result in results]

            # Compute reranking scores
            scores = BGEReranker._model.compute_score(pairs, batch_size=self.batch_size)

            # Handle single result case (scores is a float, not a list)
            if not isinstance(scores, list):
                scores = [scores]

            # Create reranked results with new scores
            reranked = []
            for result, score in zip(results, scores):
                reranked.append(SearchResult(
                    id=result.id,
                    content=result.content,
                    score=float(score),
                    metadata=result.metadata,
                    rank=0  # Will be assigned after sorting
                ))

            # Sort by BGE score descending
            reranked.sort(key=lambda x: x.score, reverse=True)

            # Assign ranks
            for rank, result in enumerate(reranked):
                result.rank = rank

            # Return top_k if specified
            if top_k is not None:
                return reranked[:top_k]

            return reranked

        except Exception as e:
            logger.error(f"BGE reranking failed: {e}", exc_info=True)
            return results


@dataclass
class PrefilterResult:
    keyword_hits: List[SearchResult]
    candidate_ids: List[str]


class HybridSearchEngine:
    def __init__(self, vector_store: VectorStore, keyword_store: VectorStore, rrf_k: int = 60):
        self.vector_store = vector_store
        self.keyword_store = keyword_store
        self.rrf_k = rrf_k  # Configurable k, default 60

    async def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        Perform hybrid search using RRF (Reciprocal Rank Fusion).
        """
        vec_results = await self.vector_store.search(query, top_k)
        kw_results = await self.keyword_store.search(query, top_k)
        
        return self.rrf_fusion(vec_results, kw_results, top_k)

    def rrf_fusion(self, vec_results: List[SearchResult], kw_results: List[SearchResult], limit: int = 10) -> List[SearchResult]:
        """
        Core RRF Algorithm: score = sum(1 / (k + rank))
        """
        scores: Dict[str, float] = {}
        doc_map: Dict[str, SearchResult] = {}
        
        # Process Vector Results
        for rank, res in enumerate(vec_results):
            if res.id not in doc_map:
                doc_map[res.id] = res
            scores[res.id] = scores.get(res.id, 0.0) + (1.0 / (self.rrf_k + rank + 1))
            
        # Process Keyword Results
        for rank, res in enumerate(kw_results):
            if res.id not in doc_map:
                doc_map[res.id] = res
            scores[res.id] = scores.get(res.id, 0.0) + (1.0 / (self.rrf_k + rank + 1))
            
        # Sort by RRF score descending
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        final_results = []
        for doc_id in sorted_ids[:limit]:
            res = doc_map[doc_id]
            # Create new result with fused score
            final_results.append(SearchResult(
                id=res.id,
                content=res.content,
                score=scores[doc_id],
                metadata=res.metadata,
                rank=0 # Will be assigned by caller if needed
            ))
            
        return final_results


class HSRSearchEngine:
    """
    Hierarchical Semantic Retrieval:
    1) PG prefilter (metadata/keyword)
    2) Qdrant vector recall (Top-50)
    3) RRF fusion
    """
    def __init__(
        self,
        vector_store: VectorStoreAdapter,
        prefilter: Callable[[str, int, Dict[str, Any]], Awaitable[PrefilterResult]],
        rrf_k: int = 60,
        vector_top_k: int = 50,
    ) -> None:
        self.vector_store = vector_store
        self.prefilter = prefilter
        self.rrf_k = rrf_k
        self.vector_top_k = vector_top_k

    async def search(
        self,
        query: str,
        top_k: int,
        filters: Dict[str, Any],
        embedding_fn: Callable[[str], Awaitable[List[float]]],
    ) -> List[SearchResult]:
        prefilter_result = await self.prefilter(query, top_k, filters)
        vec_results = await self.vector_store.search(
            query=query,
            top_k=self.vector_top_k,
            filters=filters,
            ids=prefilter_result.candidate_ids or None,
            embedding_fn=embedding_fn,
        )
        return HybridSearchEngine(self.vector_store, self.vector_store, rrf_k=self.rrf_k).rrf_fusion(
            vec_results,
            prefilter_result.keyword_hits,
            top_k,
        )

    async def rerank(self, query: str, results: List[SearchResult], top_k: Optional[int] = None) -> List[SearchResult]:
        """
        Rerank search results using BGE-Reranker.

        Args:
            query: Search query
            results: List of search results to rerank
            top_k: Number of top results to return

        Returns:
            Reranked list of search results
        """
        try:
            reranker = BGEReranker.get_instance()
            return reranker.rerank(query, results, top_k)
        except Exception as e:
            logger.error(f"Reranking failed: {e}", exc_info=True)
            return results
