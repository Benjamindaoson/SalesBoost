"""
Vector Store Infrastructure

Provides unified interface for vector database operations.
"""

from .qdrant_client import QdrantVectorStore, SearchResult

__all__ = ["QdrantVectorStore", "SearchResult"]
