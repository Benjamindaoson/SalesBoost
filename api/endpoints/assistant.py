"""Assistant API placeholder."""
from fastapi import APIRouter, Depends, HTTPException

from api.deps import require_user

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("/health")
async def assistant_health(current_user=Depends(require_user)):
    return {"status": "unavailable"}


@router.post("/invoke")
async def assistant_invoke(current_user=Depends(require_user)):
    raise HTTPException(status_code=501, detail="Assistant not implemented")
