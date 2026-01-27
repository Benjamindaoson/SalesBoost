"""Streaming ingestion pipeline stub."""
from __future__ import annotations

import uuid


class StreamingIngestionPipeline:
    async def ingest_bytes(self, source_id: str, filename: str, data: bytes, base_metadata: dict) -> dict:
        return {
            "document_id": str(uuid.uuid4()),
            "source_id": source_id,
            "filename": filename,
            "bytes": len(data),
            "metadata": base_metadata,
        }
