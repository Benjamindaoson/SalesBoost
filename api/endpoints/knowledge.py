import base64
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from api.deps import audit_access, require_admin_or_operator
from api.auth_schemas import UserSchema as User
from schemas.fsm import SalesStage
from app.agents.ask.correction_agent import correction_service
from app.tools.connectors.ingestion.streaming_pipeline import StreamingIngestionPipeline
from app.agents.study.knowledge_service import KnowledgeService

router = APIRouter(dependencies=[Depends(audit_access)])
streaming_pipeline = StreamingIngestionPipeline()


class TextIngestRequest(BaseModel):
    content: str
    source: str
    stage: SalesStage
    type: str = "script"


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
    current_user: User = Depends(require_admin_or_operator),
):
    service = KnowledgeService()
    content = (await file.read()).decode("utf-8", errors="replace")
    doc_id = service.add_document(content, {"source": file.filename, "stage": stage.value, "type": type})
    return {"id": doc_id, "status": "success"}


@router.post("/text")
async def ingest_text(
    request: TextIngestRequest,
    current_user: User = Depends(require_admin_or_operator),
):
    service = KnowledgeService()
    doc_id = service.add_document(
        request.content,
        {"source": request.source, "stage": request.stage.value, "type": request.type},
    )
    return {"id": doc_id, "status": "success"}


@router.post("/stream")
async def ingest_stream(
    request: StreamingIngestRequest,
    current_user: User = Depends(require_admin_or_operator),
):
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
async def submit_correction(
    request: CorrectionRequest,
    current_user: User = Depends(require_admin_or_operator),
):
    payload = request.model_dump()
    try:
        result = await correction_service.apply(payload)
        return {"status": "success", **result}
    except Exception:
        raise HTTPException(status_code=400, detail="correction failed")


@router.get("/stats")
async def get_stats(current_user: User = Depends(require_admin_or_operator)):
    service = KnowledgeService()
    return {"count": service.count_documents()}
