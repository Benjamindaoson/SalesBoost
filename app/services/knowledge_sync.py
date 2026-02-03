import asyncio
import logging
from typing import Any
from app.infra.events.bus import bus
from app.infra.events.schemas import EventType, KnowledgeEventPayload

logger = logging.getLogger(__name__)

# Simulated services
class ChromaIndexer:
    async def index(self, payload: KnowledgeEventPayload):
        logger.info(f"[ChromaDB] Indexing document {payload.document_id}")
        await asyncio.sleep(0.1) # Simulate IO
        logger.info(f"[ChromaDB] Indexed {payload.document_id} successfully")

class BM25Indexer:
    async def index(self, payload: KnowledgeEventPayload):
        logger.info(f"[BM25] Indexing document {payload.document_id}")
        await asyncio.sleep(0.05) # Simulate IO
        logger.info(f"[BM25] Indexed {payload.document_id} successfully")

chroma_indexer = ChromaIndexer()
bm25_indexer = BM25Indexer()

@bus.subscribe(EventType.KNOWLEDGE_UPDATED)
async def sync_chroma(payload: Any):
    # Ensure payload is typed
    if isinstance(payload, dict):
        payload = KnowledgeEventPayload(**payload)
    await chroma_indexer.index(payload)

@bus.subscribe(EventType.KNOWLEDGE_UPDATED)
async def sync_bm25(payload: Any):
    if isinstance(payload, dict):
        payload = KnowledgeEventPayload(**payload)
    await bm25_indexer.index(payload)
