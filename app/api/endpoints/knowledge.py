from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.knowledge_service import KnowledgeService
from app.schemas.fsm import SalesStage

router = APIRouter()

class TextIngestRequest(BaseModel):
    content: str
    source: str
    stage: SalesStage
    type: str = "script" # script, case, strategy

@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    stage: SalesStage = SalesStage.OPENING,
    type: str = "script"
):
    service = KnowledgeService()
    content = (await file.read()).decode("utf-8")
    doc_id = service.add_document(content, {"source": file.filename, "stage": stage.value, "type": type})
    return {"id": doc_id, "status": "success"}

@router.post("/text")
async def ingest_text(request: TextIngestRequest):
    service = KnowledgeService()
    doc_id = service.add_document(request.content, {
        "source": request.source, 
        "stage": request.stage.value, 
        "type": request.type
    })
    return {"id": doc_id, "status": "success"}

@router.get("/stats")
async def get_stats():
    service = KnowledgeService()
    return {"count": service.count_documents()}
