"""
Parent-Child Chunking Strategy

This module implements a hierarchical chunking strategy where:
- Child chunks (small, 128 tokens) are used for retrieval (high precision)
- Parent chunks (large, 512 tokens) are returned to LLM (better context)

Benefits:
- Improved retrieval precision (smaller chunks = better matching)
- Better context for LLM (larger chunks = more coherent)
- Reduced context fragmentation

Architecture:
    Document → Parent Chunks (512 tokens)
              ↓
              Child Chunks (128 tokens) → Vector Store
              ↓
              Retrieval matches child → Return parent

Usage:
    from app.tools.connectors.ingestion.parent_child_chunker import ParentChildChunker

    chunker = ParentChildChunker(
        child_size=128,
        parent_size=512
    )

    chunks = chunker.chunk_document(text)
    # Returns: List[ParentChildChunk]
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from uuid import uuid4

from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


@dataclass
class ParentChildChunk:
    """
    Represents a parent-child chunk pair

    Attributes:
        parent_id: Unique ID for parent chunk
        parent_text: Full parent chunk text (512 tokens)
        parent_start: Start position in document
        parent_end: End position in document
        child_id: Unique ID for child chunk
        child_text: Child chunk text (128 tokens)
        child_start: Start position in parent
        child_end: End position in parent
        metadata: Additional metadata
    """
    parent_id: str
    parent_text: str
    parent_start: int
    parent_end: int
    child_id: str
    child_text: str
    child_start: int
    child_end: int
    metadata: Dict[str, Any]


class ParentChildChunker:
    """
    Hierarchical chunker with parent-child relationship

    Strategy:
    1. Split document into parent chunks (512 tokens)
    2. Split each parent into child chunks (128 tokens)
    3. Store child chunks in vector store with parent reference
    4. On retrieval, return parent chunks for matched children
    """

    def __init__(
        self,
        child_size: int = 128,
        parent_size: int = 512,
        child_overlap: int = 20,
        parent_overlap: int = 50,
        separators: Optional[List[str]] = None,
    ):
        """
        Initialize parent-child chunker

        Args:
            child_size: Target size for child chunks (tokens)
            parent_size: Target size for parent chunks (tokens)
            child_overlap: Overlap between child chunks
            parent_overlap: Overlap between parent chunks
            separators: Custom separators for splitting
        """
        self.child_size = child_size
        self.parent_size = parent_size
        self.child_overlap = child_overlap
        self.parent_overlap = parent_overlap

        # Default separators (prioritize semantic boundaries)
        if separators is None:
            separators = [
                "\n\n",  # Paragraph breaks
                "\n",    # Line breaks
                "。",    # Chinese period
                ".",     # English period
                "！",    # Chinese exclamation
                "!",     # English exclamation
                "？",    # Chinese question
                "?",     # English question
                "；",    # Chinese semicolon
                ";",     # English semicolon
                " ",     # Space
                "",      # Character-level fallback
            ]

        # Create text splitters
        # Approximate: 1 token ≈ 4 characters (for Chinese/English mix)
        self.parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_size * 4,
            chunk_overlap=parent_overlap * 4,
            separators=separators,
            length_function=len,
        )

        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_size * 4,
            chunk_overlap=child_overlap * 4,
            separators=separators,
            length_function=len,
        )

        logger.info(
            f"[ParentChildChunker] Initialized: "
            f"parent={parent_size}t, child={child_size}t"
        )

    def chunk_document(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ParentChildChunk]:
        """
        Chunk document into parent-child pairs

        Args:
            text: Document text
            metadata: Document metadata

        Returns:
            List of ParentChildChunk objects
        """
        if metadata is None:
            metadata = {}

        chunks = []

        # Step 1: Split into parent chunks
        parent_texts = self.parent_splitter.split_text(text)

        logger.info(f"[ParentChildChunker] Created {len(parent_texts)} parent chunks")

        # Step 2: Split each parent into children
        parent_start = 0
        for parent_idx, parent_text in enumerate(parent_texts):
            parent_id = str(uuid4())
            parent_end = parent_start + len(parent_text)

            # Split parent into children
            child_texts = self.child_splitter.split_text(parent_text)

            logger.debug(
                f"[ParentChildChunker] Parent {parent_idx}: "
                f"{len(child_texts)} children"
            )

            # Create parent-child pairs
            child_start = 0
            for child_idx, child_text in enumerate(child_texts):
                child_id = str(uuid4())
                child_end = child_start + len(child_text)

                chunk = ParentChildChunk(
                    parent_id=parent_id,
                    parent_text=parent_text,
                    parent_start=parent_start,
                    parent_end=parent_end,
                    child_id=child_id,
                    child_text=child_text,
                    child_start=child_start,
                    child_end=child_end,
                    metadata={
                        **metadata,
                        "parent_idx": parent_idx,
                        "child_idx": child_idx,
                        "total_parents": len(parent_texts),
                        "total_children_in_parent": len(child_texts),
                    }
                )

                chunks.append(chunk)

                child_start = child_end - (self.child_overlap * 4)

            parent_start = parent_end - (self.parent_overlap * 4)

        logger.info(
            f"[ParentChildChunker] Created {len(chunks)} child chunks "
            f"from {len(parent_texts)} parents"
        )

        return chunks

    def get_storage_format(
        self,
        chunks: List[ParentChildChunk]
    ) -> Dict[str, Any]:
        """
        Convert chunks to storage format for vector store

        Returns:
            {
                "child_chunks": [  # Store these in vector store
                    {
                        "id": "child_id",
                        "text": "child_text",
                        "parent_id": "parent_id",
                        "metadata": {...}
                    }
                ],
                "parent_map": {  # Store this for retrieval
                    "parent_id": {
                        "text": "parent_text",
                        "start": 0,
                        "end": 100,
                        "metadata": {...}
                    }
                }
            }
        """
        child_chunks = []
        parent_map = {}

        for chunk in chunks:
            # Add child chunk for vector store
            child_chunks.append({
                "id": chunk.child_id,
                "text": chunk.child_text,
                "parent_id": chunk.parent_id,
                "metadata": chunk.metadata,
            })

            # Add parent to map (deduplicate by parent_id)
            if chunk.parent_id not in parent_map:
                parent_map[chunk.parent_id] = {
                    "text": chunk.parent_text,
                    "start": chunk.parent_start,
                    "end": chunk.parent_end,
                    "metadata": chunk.metadata,
                }

        return {
            "child_chunks": child_chunks,
            "parent_map": parent_map,
        }


# ==================== Integration with Existing RAG ====================

class ParentChildRetriever:
    """
    Retriever that uses parent-child chunking

    Workflow:
    1. Query → Retrieve child chunks (high precision)
    2. Get parent IDs from matched children
    3. Return parent chunks (better context)
    """

    def __init__(
        self,
        vector_store,
        parent_map: Dict[str, Dict[str, Any]],
        top_k: int = 5,
    ):
        """
        Initialize parent-child retriever

        Args:
            vector_store: Vector store containing child chunks
            parent_map: Map of parent_id → parent chunk data
            top_k: Number of results to return
        """
        self.vector_store = vector_store
        self.parent_map = parent_map
        self.top_k = top_k

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve parent chunks based on child chunk matches

        Args:
            query: Search query
            top_k: Number of results (overrides default)

        Returns:
            List of parent chunks with metadata
        """
        k = top_k or self.top_k

        # Step 1: Retrieve child chunks
        child_results = await self.vector_store.similarity_search(
            query,
            k=k * 2  # Retrieve more children to get diverse parents
        )

        # Step 2: Get unique parent IDs
        parent_ids = []
        seen = set()

        for child in child_results:
            parent_id = child.metadata.get("parent_id")
            if parent_id and parent_id not in seen:
                parent_ids.append(parent_id)
                seen.add(parent_id)

                # Stop when we have enough parents
                if len(parent_ids) >= k:
                    break

        # Step 3: Return parent chunks
        results = []
        for parent_id in parent_ids:
            if parent_id in self.parent_map:
                parent_data = self.parent_map[parent_id]
                results.append({
                    "id": parent_id,
                    "text": parent_data["text"],
                    "metadata": parent_data["metadata"],
                    "score": 1.0,  # TODO: Aggregate child scores
                })

        logger.info(
            f"[ParentChildRetriever] Retrieved {len(results)} parents "
            f"from {len(child_results)} children"
        )

        return results


# ==================== Factory Function ====================

def create_parent_child_chunker(
    child_size: int = 128,
    parent_size: int = 512,
) -> ParentChildChunker:
    """
    Create parent-child chunker with default settings

    Args:
        child_size: Child chunk size in tokens
        parent_size: Parent chunk size in tokens

    Returns:
        ParentChildChunker instance
    """
    return ParentChildChunker(
        child_size=child_size,
        parent_size=parent_size,
    )
