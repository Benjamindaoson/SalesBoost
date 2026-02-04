import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query, BackgroundTasks
from pydantic import BaseModel

from api.deps import audit_access
from schemas.fsm import SalesStage
from app.tools.connectors.ingestion.streaming_pipeline import StreamingIngestionPipeline
from app.infra.search.vector_store import VectorStoreAdapter

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(audit_access)])

# Initialize Vector Store and Pipeline
# Default collection. Can be overridden per request if needed.
DEFAULT_COLLECTION = "sales_knowledge"
vector_store = VectorStoreAdapter(collection_name=DEFAULT_COLLECTION)
streaming_pipeline = StreamingIngestionPipeline(vector_store=vector_store)

class TextIngestRequest(BaseModel):
    content: str
    source: str
    stage: SalesStage
    type: str = "script"
    collection_name: Optional[str] = DEFAULT_COLLECTION

class StreamingIngestRequest(BaseModel):
    filename: str
    content_base64: str
    source_id: str = "stream"
    metadata: Optional[Dict[str, Any]] = None
    collection_name: Optional[str] = DEFAULT_COLLECTION

class CorrectionRequest(BaseModel):
    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None
    corrected_text: str
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BulkDeleteRequest(BaseModel):
    ids: List[str]
    collection_name: Optional[str] = DEFAULT_COLLECTION

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    collection_name: Optional[str] = DEFAULT_COLLECTION
    filters: Optional[Dict[str, Any]] = None

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    collection_name: str = Query(DEFAULT_COLLECTION),
    background_tasks: BackgroundTasks = None
):
    """Upload and ingest a file."""
    try:
        content = await file.read()
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Only text files supported for now via this endpoint.")
            
        store = VectorStoreAdapter(collection_name=collection_name)
        ids = await store.add_documents([text_content], metadatas=[{"source": file.filename, "type": "file"}])
        
        return {"status": "success", "ids": ids, "count": len(ids)}
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/text")
async def upload_text(request: TextIngestRequest):
    """Ingest raw text."""
    try:
        store = VectorStoreAdapter(collection_name=request.collection_name or DEFAULT_COLLECTION)
        ids = await store.add_documents(
            [request.content], 
            metadatas=[{"source": request.source, "type": request.type, "stage": request.stage}]
        )
        return {"status": "success", "ids": ids}
    except Exception as e:
        logger.error(f"Text ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_knowledge(
    limit: int = 100, 
    offset: int = 0,
    collection_name: str = Query(DEFAULT_COLLECTION)
):
    """List knowledge entries (scroll)."""
    try:
        store = VectorStoreAdapter(collection_name=collection_name)
        await store._ensure_collection()
        # We need to access underlying client for scroll
        # Using offset as scroll id/offset if integer, or Qdrant offset
        result = await store._client.scroll(
            collection_name=collection_name,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        points, next_offset = result
        
        items = []
        for point in points:
            items.append({
                "id": point.id,
                "payload": point.payload,
                "score": 0
            })
            
        return {"items": items, "next_offset": next_offset}
    except Exception as e:
        logger.error(f"List failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_stats(collection_name: str = Query(DEFAULT_COLLECTION)):
    """Get collection stats."""
    try:
        store = VectorStoreAdapter(collection_name=collection_name)
        info = await store.get_collection_info()
        return info
    except Exception as e:
        logger.error(f"Stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id}")
async def delete_knowledge(id: str, collection_name: str = Query(DEFAULT_COLLECTION)):
    """Delete a knowledge entry."""
    try:
        store = VectorStoreAdapter(collection_name=collection_name)
        await store.delete([id])
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-delete")
async def bulk_delete(request: BulkDeleteRequest):
    """Bulk delete knowledge entries."""
    try:
        store = VectorStoreAdapter(collection_name=request.collection_name or DEFAULT_COLLECTION)
        await store.delete(request.ids)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Bulk delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collections")
async def list_collections():
    """List all knowledge collections."""
    try:
        collections = await vector_store.list_collections()
        result = []
        for name in collections:
            try:
                store = VectorStoreAdapter(collection_name=name)
                info = await store.get_collection_info()
                result.append({
                    "name": name,
                    "vector_count": info.get("vectors_count", 0),
                    "size_bytes": 0, # Placeholder
                    "status": info.get("status")
                })
            except:
                result.append({"name": name, "status": "unknown"})
        return {"collections": result}
    except Exception as e:
        logger.error(f"List collections failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/collections")
async def create_collection(name: str = Query(...)):
    """Create a new collection."""
    try:
        store = VectorStoreAdapter(collection_name=name)
        await store._ensure_collection()
        return {"status": "success", "name": name}
    except Exception as e:
        logger.error(f"Create collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/collections/{name}")
async def delete_collection(name: str):
    """Delete a collection."""
    try:
        store = VectorStoreAdapter(collection_name=name)
        success = await store.delete_collection(name)
        if not success:
             raise HTTPException(status_code=404, detail="Collection not found or failed to delete")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Delete collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
