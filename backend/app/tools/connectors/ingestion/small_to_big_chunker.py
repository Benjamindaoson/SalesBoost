"""
Small-to-Big Retrieval Chunker.

Implements parent-child chunking strategy:
- Child chunks (128 tokens): Used for high-precision retrieval
- Parent chunks (512-1024 tokens): Used as context for LLM

This solves the problem of "finding the sentence but losing the context".
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ChunkPair:
    """Represents a parent-child chunk pair."""

    parent_id: str
    parent_text: str
    parent_start: int
    parent_end: int

    child_id: str
    child_text: str
    child_start: int
    child_end: int

    metadata: Dict[str, Any]


class SmallToBigChunker:
    """
    Small-to-Big chunking strategy for RAG.

    Strategy:
    1. Split document into parent chunks (512-1024 tokens)
    2. Split each parent into child chunks (128 tokens)
    3. Store both in vector DB with parent-child relationship
    4. Retrieve using child chunks (high precision)
    5. Return parent chunks as context (full background)

    Args:
        parent_size: Size of parent chunks in characters (default: 1024)
        child_size: Size of child chunks in characters (default: 256)
        parent_overlap: Overlap between parent chunks (default: 100)
        child_overlap: Overlap between child chunks (default: 50)
    """

    def __init__(
        self,
        parent_size: int = 1024,
        child_size: int = 256,
        parent_overlap: int = 100,
        child_overlap: int = 50,
    ):
        self.parent_size = parent_size
        self.child_size = child_size
        self.parent_overlap = parent_overlap
        self.child_overlap = child_overlap

        # Validate configuration
        if child_size >= parent_size:
            raise ValueError("child_size must be smaller than parent_size")
        if parent_overlap >= parent_size:
            raise ValueError("parent_overlap must be smaller than parent_size")
        if child_overlap >= child_size:
            raise ValueError("child_overlap must be smaller than child_size")

    def chunk_text(
        self,
        text: str,
        doc_id: Optional[str] = None,
        base_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[ChunkPair]:
        """
        Chunk text into parent-child pairs.

        Args:
            text: Text to chunk
            doc_id: Document ID (generated if not provided)
            base_metadata: Base metadata to attach to all chunks

        Returns:
            List of ChunkPair objects
        """
        if not text:
            return []

        doc_id = doc_id or str(uuid.uuid4())
        base_metadata = base_metadata or {}

        # Step 1: Create parent chunks
        parent_chunks = self._create_chunks(
            text=text,
            chunk_size=self.parent_size,
            overlap=self.parent_overlap,
        )

        # Step 2: Create child chunks for each parent
        chunk_pairs: List[ChunkPair] = []

        for parent_idx, (parent_text, parent_start, parent_end) in enumerate(parent_chunks):
            parent_id = f"{doc_id}_parent_{parent_idx}"

            # Create child chunks within this parent
            child_chunks = self._create_chunks(
                text=parent_text,
                chunk_size=self.child_size,
                overlap=self.child_overlap,
            )

            for child_idx, (child_text, child_start_rel, child_end_rel) in enumerate(child_chunks):
                child_id = f"{doc_id}_child_{parent_idx}_{child_idx}"

                # Calculate absolute positions
                child_start_abs = parent_start + child_start_rel
                child_end_abs = parent_start + child_end_rel

                chunk_pair = ChunkPair(
                    parent_id=parent_id,
                    parent_text=parent_text,
                    parent_start=parent_start,
                    parent_end=parent_end,
                    child_id=child_id,
                    child_text=child_text,
                    child_start=child_start_abs,
                    child_end=child_end_abs,
                    metadata={
                        **base_metadata,
                        "doc_id": doc_id,
                        "parent_idx": parent_idx,
                        "child_idx": child_idx,
                        "chunk_type": "child",  # Mark as child for retrieval
                        "parent_id": parent_id,  # Link to parent
                    },
                )

                chunk_pairs.append(chunk_pair)

        logger.info(
            f"Created {len(chunk_pairs)} child chunks from {len(parent_chunks)} parent chunks "
            f"for document {doc_id}"
        )

        return chunk_pairs

    def _create_chunks(
        self,
        text: str,
        chunk_size: int,
        overlap: int,
    ) -> List[Tuple[str, int, int]]:
        """
        Create chunks with overlap.

        Args:
            text: Text to chunk
            chunk_size: Size of each chunk
            overlap: Overlap between chunks

        Returns:
            List of (chunk_text, start_pos, end_pos) tuples
        """
        chunks: List[Tuple[str, int, int]] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk_text = text[start:end]

            # Skip empty chunks
            if chunk_text.strip():
                chunks.append((chunk_text, start, end))

            # Move to next chunk with overlap
            start = end - overlap

            # Prevent infinite loop
            if start >= text_len:
                break

        return chunks

    def prepare_for_storage(
        self,
        chunk_pairs: List[ChunkPair],
    ) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
        """
        Prepare chunk pairs for storage in vector database.

        We store ONLY child chunks in the vector DB for retrieval.
        Parent text is stored in metadata for later retrieval.

        Args:
            chunk_pairs: List of ChunkPair objects

        Returns:
            Tuple of (ids, texts, metadatas)
        """
        ids: List[str] = []
        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for pair in chunk_pairs:
            # Store child chunk for retrieval
            ids.append(pair.child_id)
            texts.append(pair.child_text)

            # Store parent text in metadata for context retrieval
            metadata = {
                **pair.metadata,
                "parent_text": pair.parent_text,  # Full parent context
                "parent_id": pair.parent_id,
                "child_start": pair.child_start,
                "child_end": pair.child_end,
                "parent_start": pair.parent_start,
                "parent_end": pair.parent_end,
            }
            metadatas.append(metadata)

        return ids, texts, metadatas


class SmallToBigRetriever:
    """
    Retriever that uses small-to-big strategy.

    Retrieval flow:
    1. Search using child chunks (high precision)
    2. Extract parent chunks from metadata
    3. Deduplicate parent chunks
    4. Return parent chunks as context
    """

    def __init__(self, vector_store):
        """
        Initialize retriever.

        Args:
            vector_store: Vector store instance (VectorStoreAdapter)
        """
        self.vector_store = vector_store

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve parent chunks using child chunk search.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional filters

        Returns:
            List of parent chunks with metadata
        """
        # Step 1: Search using child chunks
        child_results = await self.vector_store.search(
            query=query,
            top_k=top_k * 2,  # Retrieve more to account for deduplication
            filters=filters,
        )

        # Step 2: Extract parent chunks and deduplicate
        parent_map: Dict[str, Dict[str, Any]] = {}

        for result in child_results:
            parent_id = result.metadata.get("parent_id")
            parent_text = result.metadata.get("parent_text")

            if not parent_id or not parent_text:
                logger.warning(f"Missing parent info in result {result.id}")
                continue

            # Keep the highest scoring child for each parent
            if parent_id not in parent_map or result.score > parent_map[parent_id]["score"]:
                parent_map[parent_id] = {
                    "id": parent_id,
                    "content": parent_text,
                    "score": result.score,
                    "metadata": {
                        k: v for k, v in result.metadata.items()
                        if k not in ["parent_text", "chunk_type"]
                    },
                    "child_id": result.id,
                    "child_content": result.content,
                }

        # Step 3: Sort by score and return top_k
        parents = sorted(
            parent_map.values(),
            key=lambda x: x["score"],
            reverse=True,
        )[:top_k]

        logger.info(
            f"Retrieved {len(parents)} parent chunks from {len(child_results)} child chunks"
        )

        return parents
