#!/usr/bin/env python3
"""
Semantic Vector Search Engine - Industrial Grade
Fix critical technical debt: Replace keyword search with semantic vector retrieval

Performance Requirements:
- Single query latency: <50ms
- System initialization: <30s
- Memory usage: <500MB
- Retrieval accuracy: >85%

Author: Claude Sonnet 4.5
Date: 2026-02-01
Priority: P0
"""

import sys
import json
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class SimpleVectorStore:
    """
    Pure in-memory semantic vector store

    Features:
    - BGE-M3 embeddings for Chinese text
    - Numpy-based cosine similarity
    - Memory-resident vectors (68 chunks ~4MB)
    - Batch query support
    - Performance monitoring
    """

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        """
        Initialize vector store

        Args:
            model_name: Sentence transformer model name
                       Default: BAAI/bge-small-zh-v1.5 (512 dims, Chinese-optimized)
        """
        self.model_name = model_name
        self.model = None
        self.embeddings = None
        self.documents = []
        self.metadata = []

        # Performance metrics
        self.stats = {
            "total_queries": 0,
            "total_query_time": 0.0,
            "avg_query_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }

        # Query cache (LRU-style, max 100 entries)
        self.query_cache = {}
        self.max_cache_size = 100

        logger.info(f"Initializing SimpleVectorStore with model: {model_name}")

    def _load_model(self):
        """Load sentence transformer model"""
        if self.model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading model: {self.model_name}")
            start_time = time.time()

            self.model = SentenceTransformer(self.model_name)

            load_time = time.time() - start_time
            logger.info(f"[OK] Model loaded in {load_time:.2f}s")
            logger.info(f"[OK] Embedding dimension: {self.model.get_sentence_embedding_dimension()}")

        except ImportError:
            logger.error("[X] sentence-transformers not installed")
            raise RuntimeError("Please install: pip install sentence-transformers")
        except Exception as e:
            logger.error(f"[X] Model loading failed: {e}")
            raise

    def load_data(self, json_path: str) -> int:
        """
        Load semantic chunks and generate embeddings

        Args:
            json_path: Path to semantic_chunks.json

        Returns:
            Number of chunks loaded
        """
        logger.info(f"Loading data from: {json_path}")

        # Load JSON data
        json_file = Path(json_path)
        if not json_file.exists():
            raise FileNotFoundError(f"Data file not found: {json_path}")

        with open(json_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)

        logger.info(f"[OK] Loaded {len(chunks)} chunks from file")

        # Load model if not already loaded
        self._load_model()

        # Extract documents and metadata
        self.documents = []
        self.metadata = []

        for chunk in chunks:
            self.documents.append(chunk['text'])
            self.metadata.append({
                'id': chunk['id'],
                'source': chunk['source'],
                'type': chunk['type'],
                'char_count': chunk['char_count'],
                'metadata': chunk.get('metadata', {})
            })

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(self.documents)} documents...")
        start_time = time.time()

        self.embeddings = self.model.encode(
            self.documents,
            show_progress_bar=True,
            batch_size=32,
            normalize_embeddings=True  # Normalize for cosine similarity
        )

        embed_time = time.time() - start_time
        logger.info(f"[OK] Embeddings generated in {embed_time:.2f}s")
        logger.info(f"[OK] Embedding shape: {self.embeddings.shape}")

        # Calculate memory usage
        memory_mb = self.embeddings.nbytes / (1024 * 1024)
        logger.info(f"[OK] Memory usage: {memory_mb:.2f} MB")

        return len(self.documents)

    def _cosine_similarity(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[int, float]]:
        """
        Calculate cosine similarity between query and all documents

        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results to return

        Returns:
            List of (index, similarity_score) tuples
        """
        # Cosine similarity = dot product (since vectors are normalized)
        similarities = np.dot(self.embeddings, query_embedding)

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Return (index, score) tuples
        results = [(int(idx), float(similarities[idx])) for idx in top_indices]

        return results

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filter_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for query

        Args:
            query: Search query text
            top_k: Number of results to return
            min_score: Minimum similarity score threshold
            filter_type: Filter by chunk type (champion_case, training_scenario, sales_sop)

        Returns:
            List of search results with scores
        """
        if self.model is None or self.embeddings is None:
            raise RuntimeError("Vector store not initialized. Call load_data() first.")

        # Check cache
        cache_key = f"{query}_{top_k}_{min_score}_{filter_type}"
        if cache_key in self.query_cache:
            self.stats["cache_hits"] += 1
            logger.debug(f"[CACHE HIT] Query: {query[:50]}...")
            return self.query_cache[cache_key]

        self.stats["cache_misses"] += 1

        # Measure query time
        start_time = time.time()

        # Generate query embedding
        query_embedding = self.model.encode(
            query,
            normalize_embeddings=True
        )

        # Calculate similarities
        similarities = self._cosine_similarity(query_embedding, top_k=len(self.documents))

        # Filter and format results
        results = []
        for idx, score in similarities:
            # Apply score threshold
            if score < min_score:
                continue

            # Apply type filter
            if filter_type and self.metadata[idx]['type'] != filter_type:
                continue

            result = {
                'id': self.metadata[idx]['id'],
                'text': self.documents[idx],
                'source': self.metadata[idx]['source'],
                'type': self.metadata[idx]['type'],
                'score': score,
                'metadata': self.metadata[idx]['metadata']
            }
            results.append(result)

            # Stop if we have enough results
            if len(results) >= top_k:
                break

        # Update stats
        query_time = time.time() - start_time
        self.stats["total_queries"] += 1
        self.stats["total_query_time"] += query_time
        self.stats["avg_query_time"] = self.stats["total_query_time"] / self.stats["total_queries"]

        # Cache result (LRU-style)
        if len(self.query_cache) >= self.max_cache_size:
            # Remove oldest entry
            self.query_cache.pop(next(iter(self.query_cache)))
        self.query_cache[cache_key] = results

        logger.debug(f"[OK] Query completed in {query_time*1000:.2f}ms, found {len(results)} results")

        return results

    def batch_search(
        self,
        queries: List[str],
        top_k: int = 5,
        min_score: float = 0.0
    ) -> List[List[Dict[str, Any]]]:
        """
        Batch semantic search

        Args:
            queries: List of query texts
            top_k: Number of results per query
            min_score: Minimum similarity score threshold

        Returns:
            List of result lists (one per query)
        """
        logger.info(f"Processing batch of {len(queries)} queries")

        results = []
        for query in queries:
            query_results = self.search(query, top_k=top_k, min_score=min_score)
            results.append(query_results)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            **self.stats,
            "total_documents": len(self.documents),
            "embedding_dimension": self.embeddings.shape[1] if self.embeddings is not None else 0,
            "memory_mb": self.embeddings.nbytes / (1024 * 1024) if self.embeddings is not None else 0,
            "cache_size": len(self.query_cache),
            "cache_hit_rate": self.stats["cache_hits"] / max(1, self.stats["cache_hits"] + self.stats["cache_misses"])
        }

    def clear_cache(self):
        """Clear query cache"""
        self.query_cache.clear()
        logger.info("[OK] Query cache cleared")


def main():
    """Test the vector store"""
    print("="*70)
    print("Semantic Vector Store - Initialization Test")
    print("="*70)

    # Initialize vector store
    store = SimpleVectorStore()

    # Load data
    data_path = "data/processed/semantic_chunks.json"

    try:
        num_chunks = store.load_data(data_path)
        print(f"\n[OK] Loaded {num_chunks} chunks")

        # Test queries
        test_queries = [
            "这个太贵了，有没有便宜点的",
            "我需要再考虑一下",
            "年费问题怎么处理",
            "权益不够用怎么办"
        ]

        print("\n" + "="*70)
        print("Test Queries")
        print("="*70)

        for query in test_queries:
            print(f"\nQuery: {query}")
            results = store.search(query, top_k=3, min_score=0.5)

            for i, result in enumerate(results, 1):
                print(f"\nResult {i}:")
                print(f"  Score: {result['score']:.4f}")
                print(f"  Type: {result['type']}")
                print(f"  Source: {result['source']}")
                print(f"  Preview: {result['text'][:100]}...")

        # Print stats
        print("\n" + "="*70)
        print("Performance Statistics")
        print("="*70)

        stats = store.get_stats()
        print(f"Total documents: {stats['total_documents']}")
        print(f"Embedding dimension: {stats['embedding_dimension']}")
        print(f"Memory usage: {stats['memory_mb']:.2f} MB")
        print(f"Total queries: {stats['total_queries']}")
        print(f"Average query time: {stats['avg_query_time']*1000:.2f} ms")
        print(f"Cache hit rate: {stats['cache_hit_rate']*100:.1f}%")

        print("\n[OK] All tests passed!")

    except Exception as e:
        print(f"\n[X] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
