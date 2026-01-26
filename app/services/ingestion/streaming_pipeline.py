import asyncio
import hashlib
import logging
import tempfile
from pathlib import Path
from typing import AsyncIterator, Callable, Dict, Any, Optional, List

from watchfiles import awatch, Change

from app.services.enhanced_document_parser import EnhancedDocumentParser
from app.services.ingestion.semantic_chunker import SemanticChunker
from app.services.knowledge_service import KnowledgeService
from app.services.graph_rag_service import GraphRAGService
from app.services.audio_service import audio_service

logger = logging.getLogger(__name__)


class StreamingIngestionPipeline:
    """
    Streaming ingestion pipeline that reuses the deterministic chunker and updates
    both vector DB (Chroma) and GraphRAG in near real-time.
    """

    def __init__(self, max_tokens: int = 500):
        self.parser = EnhancedDocumentParser()
        self.chunker = SemanticChunker(max_tokens=max_tokens)
        self.knowledge = KnowledgeService()
        self.graph = GraphRAGService()

    async def ingest_bytes(
        self,
        source_id: str,
        filename: str,
        data: bytes,
        base_metadata: Optional[Dict[str, Any]] = None,
        on_chunk: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> Dict[str, Any]:
        base_metadata = base_metadata or {}
        suffix = Path(filename).suffix.lower()
        if suffix in [".mp3", ".wav", ".m4a"]:
            return await self._ingest_audio(source_id, filename, data, base_metadata, on_chunk)

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)

        parsed = self.parser.parse(tmp_path)
        text = parsed.get("markdown") or parsed.get("text") or ""
        doc_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()

        chunks = self.chunker.chunk_document(
            text=text,
            source_id=source_id,
            doc_sha256=doc_sha,
            base_metadata={**base_metadata, **parsed.get("metadata", {})},
        )

        for chunk in chunks:
            content = chunk.pop("content")
            chunk_id = chunk.get("chunk_id") or f"{source_id}:{chunk.get('chunk_index')}"
            self.knowledge.upsert_document(content=content, meta=chunk, doc_id=chunk_id)
            try:
                await self.graph.ingest_document(doc_id=chunk_id, text=content, metadata=chunk)
            except Exception as e:
                logger.warning(f"Graph ingestion failed for {chunk_id}: {e}")
            if on_chunk:
                on_chunk({"chunk_id": chunk_id, "meta": chunk})

        tmp_path.unlink(missing_ok=True)
        return {"doc_sha": doc_sha, "chunks": len(chunks)}

    async def _ingest_audio(
        self,
        source_id: str,
        filename: str,
        data: bytes,
        base_metadata: Dict[str, Any],
        on_chunk: Optional[Callable[[Dict[str, Any]], Any]],
    ) -> Dict[str, Any]:
        try:
            import io

            stream = io.BytesIO(data)
            diarized = await audio_service.transcribe_with_diarization(stream)
            text = diarized.get("text", "")
            segments = diarized.get("segments", [])
            doc_sha = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else hashlib.sha256(data).hexdigest()
            total_chunks = 0
            for idx, seg in enumerate(segments):
                seg_text = seg.get("text", "")
                if not seg_text.strip():
                    continue
                chunk_id = f"{source_id}:{doc_sha}:audio:{idx}"
                meta = {
                    "chunk_id": chunk_id,
                    "source_id": source_id,
                    "doc_sha256": doc_sha,
                    "section_path": "audio",
                    "chunk_index": idx,
                    "semantic_type": "audio_transcript",
                    "role": seg.get("role"),
                    "speaker_raw": seg.get("speaker_raw"),
                    **base_metadata,
                }
                self.knowledge.upsert_document(content=seg_text, meta=meta, doc_id=chunk_id)
                try:
                    await self.graph.ingest_document(doc_id=chunk_id, text=seg_text, metadata=meta)
                except Exception as e:
                    logger.warning(f"Graph ingestion failed for audio chunk {chunk_id}: {e}")
                total_chunks += 1
                if on_chunk:
                    on_chunk({"chunk_id": chunk_id, "meta": meta})
            return {"doc_sha": doc_sha, "chunks": total_chunks, "mode": "audio"}
        except Exception as e:
            logger.error(f"Audio ingestion failed for {filename}: {e}")
            raise

    async def consume_queue(self, queue: "asyncio.Queue[Dict[str, Any]]"):
        while True:
            payload = await queue.get()
            try:
                await self.ingest_bytes(
                    source_id=payload.get("source_id", "stream"),
                    filename=payload.get("filename", "document"),
                    data=payload.get("data", b""),
                    base_metadata=payload.get("metadata", {}),
                )
            except Exception as e:
                logger.error(f"Streaming ingestion failed: {e}")
            finally:
                queue.task_done()

    async def watch_directory(self, directory: Path, patterns: Optional[List[str]] = None):
        patterns = patterns or ["*.pdf", "*.docx", "*.txt", "*.md", "*.png", "*.jpg", "*.jpeg", "*.mp3", "*.wav", "*.m4a"]
        directory = Path(directory)
        async for changes in awatch(directory, recursive=True):
            for change, path in changes:
                if change not in {Change.added, Change.modified}:
                    continue
                file_path = Path(path)
                if not any(file_path.match(pat) for pat in patterns):
                    continue
                try:
                    data = file_path.read_bytes()
                    await self.ingest_bytes(
                        source_id=str(file_path.stem),
                        filename=file_path.name,
                        data=data,
                        base_metadata={"source_path": str(file_path)},
                    )
                    logger.info(f"Stream-ingested {file_path}")
                except Exception as e:
                    logger.error(f"Failed to stream-ingest {file_path}: {e}")
