"""Streaming ingestion pipeline with Smart Routing and Small-to-Big chunking."""
from __future__ import annotations

import codecs
import logging
import uuid
from typing import Optional

from app.infra.search.vector_store import VectorStore
from app.tools.connectors.ingestion.small_to_big_chunker import SmallToBigChunker
from app.tools.connectors.ingestion.smart_router import SmartIngestionRouter
from app.tools.connectors.ingestion.processors import process_document

logger = logging.getLogger(__name__)


class StreamingIngestionPipeline:
    """
    Streaming ingestion pipeline with support for:
    1. Smart routing (cost-optimized processing)
    2. Small-to-Big chunking (context-aware retrieval)
    3. Traditional fixed-size chunking (legacy mode)

    Philosophy: "Use the right tool for the job"
    - Simple PDFs → PyMuPDF (fast, cheap)
    - Complex PDFs → DeepSeek-OCR-2 (slow, expensive, accurate)
    - Audio → Whisper (transcription)
    - Video → Video-LLaVA (multimodal understanding)

    Args:
        vector_store: Vector store instance
        chunk_size: Size of chunks in legacy mode (default: 500)
        overlap: Overlap between chunks in legacy mode (default: 50)
        use_small_to_big: Enable Small-to-Big chunking (default: True)
        use_smart_routing: Enable smart routing (default: True)
        parent_size: Parent chunk size for Small-to-Big (default: 1024)
        child_size: Child chunk size for Small-to-Big (default: 256)
    """

    def __init__(
        self,
        vector_store=None,
        chunk_size: int = 500,
        overlap: int = 50,
        use_small_to_big: bool = True,
        use_smart_routing: bool = True,
        parent_size: int = 1024,
        child_size: int = 256,
    ):
        self.vector_store = vector_store or VectorStore()
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.use_small_to_big = use_small_to_big
        self.use_smart_routing = use_smart_routing

        # Initialize Smart Router
        if use_smart_routing:
            self.router = SmartIngestionRouter()
            logger.info("Initialized Smart Router for cost-optimized processing")
        else:
            self.router = None

        # Initialize Small-to-Big chunker if enabled
        if use_small_to_big:
            self.chunker = SmallToBigChunker(
                parent_size=parent_size,
                child_size=child_size,
                parent_overlap=overlap * 2,  # More overlap for parent chunks
                child_overlap=overlap,
            )
            logger.info(
                f"Initialized Small-to-Big chunker: "
                f"parent={parent_size}, child={child_size}"
            )
        else:
            self.chunker = None
            logger.info(f"Using legacy chunking: size={chunk_size}, overlap={overlap}")

    async def ingest_bytes(
        self,
        source_id: str,
        filename: str,
        data: bytes,
        base_metadata: dict,
    ) -> dict:
        """
        Ingest bytes with smart routing and automatic chunking.

        Workflow:
        1. Smart Router evaluates complexity
        2. Route to appropriate processor
        3. Extract text/markdown
        4. Apply chunking strategy
        5. Store in vector database

        Args:
            source_id: Source identifier
            filename: Filename
            data: Raw bytes
            base_metadata: Base metadata to attach

        Returns:
            Ingestion result with status and statistics
        """
        try:
            # Step 1: Smart routing (if enabled)
            if self.use_smart_routing and self.router:
                routing_decision = self.router.route(data, filename)

                logger.info(
                    f"Routing decision for {filename}: "
                    f"processor={routing_decision.processor}, "
                    f"complexity={routing_decision.complexity}, "
                    f"cost={routing_decision.estimated_cost:.3f}, "
                    f"reason={routing_decision.reasoning}"
                )

                # Step 2: Process with selected processor
                text = await process_document(
                    content=data,
                    filename=filename,
                    processor_name=routing_decision.processor,
                    metadata=routing_decision.metadata,
                )

                # Add routing info to metadata
                base_metadata.update(
                    {
                        "processor": routing_decision.processor,
                        "complexity": routing_decision.complexity,
                        "data_type": routing_decision.data_type,
                    }
                )

            else:
                # Legacy: decode as text
                decoder = codecs.getincrementaldecoder("utf-8")("ignore")
                text = ""

                for offset in range(0, len(data), 4096):
                    text += decoder.decode(data[offset : offset + 4096])

                text += decoder.decode(b"", final=True)

            # Step 3: Apply chunking strategy
            if self.use_small_to_big and self.chunker:
                return await self._ingest_with_small_to_big(
                    source_id=source_id,
                    filename=filename,
                    text=text,
                    base_metadata=base_metadata,
                )
            else:
                return await self._ingest_with_legacy_chunking(
                    source_id=source_id,
                    filename=filename,
                    text=text,
                    base_metadata=base_metadata,
                )

        except Exception as e:
            logger.error("Ingestion failed: %s", e, exc_info=True)
            return {"error": str(e), "status": "failed"}

    async def _ingest_with_small_to_big(
        self,
        source_id: str,
        filename: str,
        text: str,
        base_metadata: dict,
    ) -> dict:
        """
        Ingest using Small-to-Big chunking strategy.

        This creates parent-child chunk pairs and stores child chunks
        for retrieval while keeping parent text in metadata.
        """
        doc_id = str(uuid.uuid4())

        # Create chunk pairs
        chunk_pairs = self.chunker.chunk_text(
            text=text,
            doc_id=doc_id,
            base_metadata={
                **base_metadata,
                "source_id": source_id,
                "filename": filename,
            },
        )

        if not chunk_pairs:
            logger.warning(f"No chunks created for {filename}")
            return {
                "document_id": doc_id,
                "source_id": source_id,
                "filename": filename,
                "chunks_count": 0,
                "status": "empty",
            }

        # Prepare for storage
        ids, texts, metadatas = self.chunker.prepare_for_storage(chunk_pairs)

        # Store in batches
        batch_size = 50
        total_stored = 0

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_texts = texts[i : i + batch_size]
            batch_metas = metadatas[i : i + batch_size]

            await self.vector_store.add_documents(
                documents=batch_texts,
                metadatas=batch_metas,
                ids=batch_ids,
            )

            total_stored += len(batch_ids)

        logger.info(
            f"Ingested {filename}: {total_stored} child chunks "
            f"from {len(set(p.parent_id for p in chunk_pairs))} parent chunks"
        )

        return {
            "document_id": doc_id,
            "source_id": source_id,
            "filename": filename,
            "chunks_count": total_stored,
            "parent_chunks_count": len(set(p.parent_id for p in chunk_pairs)),
            "chunking_strategy": "small_to_big",
            "status": "indexed",
        }

    async def _ingest_with_legacy_chunking(
        self,
        source_id: str,
        filename: str,
        text: str,
        base_metadata: dict,
    ) -> dict:
        """
        Ingest using legacy fixed-size chunking.

        This is the original implementation for backward compatibility.
        """
        chunk_index = 0
        batch_docs = []
        batch_meta = []
        batch_ids = []
        batch_size = 50

        async def flush_batch():
            if batch_docs:
                await self.vector_store.add_documents(batch_docs, batch_meta, batch_ids)
                batch_docs.clear()
                batch_meta.clear()
                batch_ids.clear()

        async def enqueue_chunk(chunk_text: str):
            nonlocal chunk_index
            if not chunk_text:
                return
            batch_docs.append(chunk_text)
            batch_meta.append(
                {
                    **base_metadata,
                    "source_id": source_id,
                    "chunk_index": chunk_index,
                    "filename": filename,
                }
            )
            batch_ids.append(f"{source_id}_{chunk_index}")
            chunk_index += 1
            if len(batch_docs) >= batch_size:
                await flush_batch()

        # Simple sliding window chunking
        buffer = text
        while len(buffer) >= self.chunk_size:
            chunk_text = buffer[: self.chunk_size]
            await enqueue_chunk(chunk_text)
            buffer = buffer[self.chunk_size - self.overlap :]

        if buffer:
            await enqueue_chunk(buffer)

        await flush_batch()

        return {
            "document_id": str(uuid.uuid4()),
            "source_id": source_id,
            "filename": filename,
            "chunks_count": chunk_index,
            "chunking_strategy": "legacy",
            "status": "indexed",
        }
