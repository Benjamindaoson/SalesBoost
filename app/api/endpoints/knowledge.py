import base64
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.services.knowledge_service import KnowledgeService
from app.schemas.fsm import SalesStage
from app.services.ingestion.streaming_pipeline import StreamingIngestionPipeline
from app.services.correction_service import correction_service

router = APIRouter()
streaming_pipeline = StreamingIngestionPipeline()


class TextIngestRequest(BaseModel):
    content: str
    source: str
    stage: SalesStage
    type: str = "script"  # script, case, strategy


class StreamingIngestRequest(BaseModel):
    filename: str
    content_base64: str
    source_id: str = "stream"
    metadata: Optional[Dict[str, Any]] = None


class CorrectionRequest(BaseModel):
    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None
    corrected_text: str
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    stage: SalesStage = SalesStage.OPENING,
    type: str = "script",
):
    service = KnowledgeService()
    content = (await file.read()).decode("utf-8")
    doc_id = service.add_document(content, {"source": file.filename, "stage": stage.value, "type": type})
    return {"id": doc_id, "status": "success"}


@router.post("/text")
async def ingest_text(request: TextIngestRequest):
    service = KnowledgeService()
    doc_id = service.add_document(
        request.content,
        {"source": request.source, "stage": request.stage.value, "type": request.type},
    )
    return {"id": doc_id, "status": "success"}


@router.post("/stream")
async def ingest_stream(request: StreamingIngestRequest):
    try:
        data = base64.b64decode(request.content_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="content_base64 is not valid base64")
    result = await streaming_pipeline.ingest_bytes(
        source_id=request.source_id,
        filename=request.filename,
        data=data,
        base_metadata=request.metadata or {},
    )
    return {"status": "success", **result}


@router.post("/correction")
async def submit_correction(request: CorrectionRequest):
    payload = request.model_dump()
    try:
        result = await correction_service.apply(payload)
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats")
async def get_stats():
    service = KnowledgeService()
    return {"count": service.count_documents()}
