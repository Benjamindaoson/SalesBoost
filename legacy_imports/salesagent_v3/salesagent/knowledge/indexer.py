"""Knowledge Indexer — document chunking, embedding, and pgvector ingestion."""
from __future__ import annotations

import io
import uuid
from typing import Any

import structlog

log = structlog.get_logger()

CHUNK_SIZE = 512  # tokens (approximate characters / 1.5)
CHUNK_OVERLAP = 50


def _split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Simple recursive character splitter."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


class KnowledgeIndexer:
    """
    Processes uploaded documents:
    1. Extract text from PDF/DOCX/TXT/Markdown
    2. Split into overlapping chunks
    3. Embed each chunk
    4. Upsert into pgvector (knowledge_chunks table)
    5. Store original file in MinIO
    """

    def __init__(self, db: Any, minio_client: Any | None = None) -> None:
        self.db = db
        self.minio = minio_client

    async def index(
        self, file_bytes: bytes, filename: str, document_id: str | None = None
    ) -> dict[str, Any]:
        """Index a document. Returns indexing summary."""
        document_id = document_id or str(uuid.uuid4())

        # Extract text
        text = await self._extract_text(file_bytes, filename)
        if not text.strip():
            return {"document_id": document_id, "chunks": 0, "status": "empty"}

        # Split
        chunks = _split_text(text)

        # Store in MinIO
        minio_key = f"documents/{document_id}/{filename}"
        if self.minio:
            await self._store_minio(file_bytes, minio_key)

        # Embed + upsert
        from salesagent.core.settings import settings
        embeddings = await self._embed_batch(chunks)

        from salesagent.models.db_models import KnowledgeChunk

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_obj = KnowledgeChunk(
                document_name=filename,
                document_id=document_id,
                chunk_index=i,
                content=chunk,
                embedding=embedding if any(e != 0.0 for e in embedding) else None,
                metadata_={"filename": filename, "chunk_index": i, "total_chunks": len(chunks)},
                minio_key=minio_key,
            )
            self.db.add(chunk_obj)

        await self.db.commit()
        log.info("Indexed document", document_id=document_id, chunks=len(chunks), filename=filename)
        return {"document_id": document_id, "chunks": len(chunks), "status": "ok"}

    async def _extract_text(self, file_bytes: bytes, filename: str) -> str:
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if ext == "pdf":
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                return " ".join(p.extract_text() or "" for p in reader.pages)
            except Exception:
                return file_bytes.decode("utf-8", errors="ignore")
        elif ext == "docx":
            try:
                import docx
                doc = docx.Document(io.BytesIO(file_bytes))
                return "\n".join(p.text for p in doc.paragraphs)
            except Exception:
                return file_bytes.decode("utf-8", errors="ignore")
        else:
            return file_bytes.decode("utf-8", errors="ignore")

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        from salesagent.core.settings import settings
        if settings.mock_llm:
            return [[0.0] * settings.embedding_dimension for _ in texts]
        try:
            import openai
            import asyncio
            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.embeddings.create(
                model=settings.embedding_model,
                input=texts[:100],  # batch limit
            )
            return [item.embedding for item in resp.data]
        except Exception:
            return [[0.0] * settings.embedding_dimension for _ in texts]

    async def _store_minio(self, data: bytes, key: str) -> None:
        from salesagent.core.settings import settings
        try:
            import asyncio
            from minio import Minio
            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            await asyncio.to_thread(
                lambda: client.put_object(
                    settings.minio_knowledge_bucket,
                    key,
                    io.BytesIO(data),
                    length=len(data),
                )
            )
        except Exception as exc:
            log.warning("MinIO storage failed", error=str(exc))
