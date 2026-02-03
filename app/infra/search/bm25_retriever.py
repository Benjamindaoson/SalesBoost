"""
BM25 Retriever Implementation for SalesBoost RAG System.

Provides keyword-based retrieval using BM25 algorithm with Chinese text support.
"""
import logging
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

try:
    import jieba
except ImportError:
    jieba = None

from app.infra.search.vector_store import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class BM25Document:
    """Document for BM25 indexing."""
    id: str
    content: str
    metadata: Dict[str, Any]
    tokens: List[str]


class BM25Retriever:
    """
    BM25-based keyword retriever with Chinese text support.

    Features:
    - Chinese word segmentation using jieba
    - Async interface for consistency with vector retriever
    - Metadata filtering support
    - Configurable tokenization
    """

    def __init__(
        self,
        documents: Optional[List[Dict[str, Any]]] = None,
        use_jieba: bool = True,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        """
        Initialize BM25 retriever.

        Args:
            documents: Initial documents to index
            use_jieba: Use jieba for Chinese tokenization
            k1: BM25 k1 parameter (term frequency saturation)
            b: BM25 b parameter (length normalization)
        """
        if BM25Okapi is None:
            raise ImportError("rank_bm25 is not installed. Install with: pip install rank-bm25")

        self.use_jieba = use_jieba and jieba is not None
        self.k1 = k1
        self.b = b
        self.documents: List[BM25Document] = []
        self.bm25: Optional[BM25Okapi] = None

        if documents:
            self.index_documents(documents)

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text with Chinese support.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        if not text:
            return []

        # Convert to lowercase
        text = text.lower()

        if self.use_jieba:
            # Use jieba for Chinese text
            tokens = list(jieba.cut_for_search(text))
        else:
            # Simple whitespace tokenization for English
            tokens = text.split()

        # Filter out empty tokens
        tokens = [t.strip() for t in tokens if t.strip()]

        return tokens

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Index documents for BM25 retrieval.

        Args:
            documents: List of documents with 'id', 'content', and 'metadata'
        """
        self.documents = []

        for doc in documents:
            doc_id = doc.get("id", "")
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            tokens = self._tokenize(content)

            self.documents.append(BM25Document(
                id=str(doc_id),
                content=content,
                metadata=metadata,
                tokens=tokens
            ))

        # Build BM25 index
        if self.documents:
            tokenized_corpus = [doc.tokens for doc in self.documents]
            self.bm25 = BM25Okapi(tokenized_corpus, k1=self.k1, b=self.b)
            logger.info(f"BM25 index built with {len(self.documents)} documents")
        else:
            self.bm25 = None
            logger.warning("No documents to index for BM25")

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add new documents to existing index.

        Args:
            documents: List of documents to add
        """
        # Append new documents
        for doc in documents:
            doc_id = doc.get("id", "")
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            tokens = self._tokenize(content)

            self.documents.append(BM25Document(
                id=str(doc_id),
                content=content,
                metadata=metadata,
                tokens=tokens
            ))

        # Rebuild index
        if self.documents:
            tokenized_corpus = [doc.tokens for doc in self.documents]
            self.bm25 = BM25Okapi(tokenized_corpus, k1=self.k1, b=self.b)
            logger.info(f"BM25 index rebuilt with {len(self.documents)} documents")

    def _apply_filters(
        self,
        documents: List[BM25Document],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[BM25Document]:
        """
        Apply metadata filters to documents.

        Args:
            documents: Documents to filter
            filters: Metadata filters

        Returns:
            Filtered documents
        """
        if not filters:
            return documents

        filtered = []
        for doc in documents:
            match = True
            for key, value in filters.items():
                doc_value = doc.metadata.get(key)

                if isinstance(value, (list, tuple, set)):
                    # Match any value in list
                    if doc_value not in value:
                        match = False
                        break
                else:
                    # Exact match
                    if doc_value != value:
                        match = False
                        break

            if match:
                filtered.append(doc)

        return filtered

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search documents using BM25.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Metadata filters

        Returns:
            List of search results
        """
        if not self.bm25 or not self.documents:
            logger.warning("BM25 index is empty, returning no results")
            return []

        # Tokenize query
        query_tokens = self._tokenize(query)

        if not query_tokens:
            logger.warning("Query tokenization resulted in empty tokens")
            return []

        # Run BM25 search in thread pool (BM25 is CPU-bound)
        loop = asyncio.get_running_loop()
        scores = await loop.run_in_executor(
            None,
            lambda: self.bm25.get_scores(query_tokens)
        )

        # Apply filters
        filtered_docs = self._apply_filters(self.documents, filters)

        if not filtered_docs:
            logger.warning("No documents match the filters")
            return []

        # Create filtered indices mapping
        filtered_indices = {id(doc): idx for idx, doc in enumerate(self.documents) if doc in filtered_docs}

        # Get top-k results from filtered documents
        doc_scores = []
        for idx, doc in enumerate(self.documents):
            if id(doc) in filtered_indices:
                doc_scores.append((idx, scores[idx], doc))

        # Sort by score descending
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        # Take top-k
        top_results = doc_scores[:top_k]

        # Convert to SearchResult
        results = []
        for rank, (idx, score, doc) in enumerate(top_results):
            results.append(SearchResult(
                id=doc.id,
                content=doc.content,
                score=float(score),
                metadata=doc.metadata,
                rank=rank
            ))

        logger.info(f"BM25 search returned {len(results)} results for query: {query[:50]}...")
        return results

    def get_document_count(self) -> int:
        """Get number of indexed documents."""
        return len(self.documents)

    def clear(self) -> None:
        """Clear all indexed documents."""
        self.documents = []
        self.bm25 = None
        logger.info("BM25 index cleared")


class AsyncBM25Adapter:
    """
    Async adapter for BM25Retriever to match VectorStore interface.

    This adapter allows BM25Retriever to be used interchangeably with
    VectorStoreAdapter in hybrid search scenarios.
    """

    def __init__(self, retriever: BM25Retriever):
        """
        Initialize adapter.

        Args:
            retriever: BM25Retriever instance
        """
        self.retriever = retriever

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search using BM25.

        Args:
            query: Search query
            top_k: Number of results
            filters: Metadata filters

        Returns:
            List of search results
        """
        return await self.retriever.search(query, top_k, filters)

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Index documents."""
        self.retriever.index_documents(documents)

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents."""
        self.retriever.add_documents(documents)

    def get_document_count(self) -> int:
        """Get document count."""
        return self.retriever.get_document_count()

    def clear(self) -> None:
        """Clear index."""
        self.retriever.clear()
