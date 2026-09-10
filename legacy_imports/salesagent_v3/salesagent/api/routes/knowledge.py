"""Knowledge Base API."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from salesagent.dependencies import get_db
from salesagent.models.db_models import KnowledgeChunk
from salesagent.models.schemas import RetrievalTestRequest, RetrievalTestResponse
from salesagent.auth.dependencies import get_current_user
from salesagent.auth.permissions import require_admin

log = structlog.get_logger()
router = APIRouter()


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),  # Admin only
) -> dict:
    log.info("Upload document", filename=file.filename, user=current_user.get("sub"))
    from salesagent.knowledge.indexer import KnowledgeIndexer
    file_bytes = await file.read()
    indexer = KnowledgeIndexer(db=db)
    result = await indexer.index(file_bytes=file_bytes, filename=file.filename or "unknown")
    return result


@router.get("/chunks")
async def list_chunks(
    document_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    log.info("List chunks", document_id=document_id, user=current_user.get("sub"))
    q = select(KnowledgeChunk).order_by(KnowledgeChunk.created_at.desc()).limit(limit).offset(offset)
    if document_id:
        q = q.where(KnowledgeChunk.document_id == document_id)
    result = await db.execute(q)
    chunks = result.scalars().all()
    return [
        {"id": c.id, "document_name": c.document_name, "chunk_index": c.chunk_index, "content": c.content}
        for c in chunks
    ]


@router.post("/test-retrieval", response_model=RetrievalTestResponse)
async def test_retrieval(
    body: RetrievalTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RetrievalTestResponse:
    import time
    from salesagent.llm.gateway import ModelGateway
    from salesagent.knowledge.retriever import KnowledgeRetriever

    gateway = ModelGateway()
    await gateway.initialize()
    retriever = KnowledgeRetriever(db=db, gateway=gateway)

    start = time.perf_counter()
    results = await retriever.retrieve(query=body.query, top_k=body.top_k)
    latency_ms = (time.perf_counter() - start) * 1000

    return RetrievalTestResponse(
        results=[{k: v for k, v in r.items() if k != "embedding"} for r in results],
        latency_ms=round(latency_ms, 2),
    )
