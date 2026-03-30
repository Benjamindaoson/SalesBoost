"""
Test endpoint - No authentication required
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    message: str
    endpoints_available: list[str]


@router.get("/test", response_model=HealthResponse)
async def test_endpoint():
    """
    Test endpoint to verify API is working
    """
    return HealthResponse(
        status="ok",
        message="Backend API is working!",
        endpoints_available=[
            "/api/v1/tasks",
            "/api/v1/statistics",
            "/api/v1/test"
        ]
    )
