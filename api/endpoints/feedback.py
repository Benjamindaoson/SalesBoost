"""Feedback API placeholder."""
from fastapi import APIRouter, Depends, HTTPException

from api.deps import require_user

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("/health")
async def feedback_health(current_user=Depends(require_user)):
    return {"status": "unavailable"}


@router.post("/submit")
async def feedback_submit(current_user=Depends(require_user)):
    raise HTTPException(status_code=501, detail="Feedback not implemented")
