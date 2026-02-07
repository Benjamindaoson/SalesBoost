
import logging
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import get_settings
from core.database import init_db, close_db
from api.endpoints import tasks, knowledge, sessions, customers
from api.endpoints.admin_modules import analytics, courses, personas, evaluation, scenarios

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    logger.info("Starting up SalesBoost API...")
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Continue even if DB fails, to allow debugging or fallback modes
    
    yield
    
    logger.info("Shutting down SalesBoost API...")
    await close_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS Configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include Routers
app.include_router(tasks.router, prefix=f"{settings.API_V1_STR}/tasks", tags=["tasks"])
app.include_router(sessions.router, prefix=f"{settings.API_V1_STR}/sessions", tags=["sessions"])
app.include_router(customers.router, prefix=f"{settings.API_V1_STR}/customers", tags=["customers"])
app.include_router(knowledge.router, prefix=f"{settings.API_V1_STR}/knowledge", tags=["knowledge"])

# Admin Modules
app.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/admin/analytics", tags=["admin-analytics"])
app.include_router(courses.router, prefix=f"{settings.API_V1_STR}/courses", tags=["courses"])
app.include_router(personas.router, prefix=f"{settings.API_V1_STR}/personas", tags=["personas"])
app.include_router(evaluation.router, prefix=f"{settings.API_V1_STR}/evaluation", tags=["evaluation"])
app.include_router(scenarios.router, prefix=f"{settings.API_V1_STR}/scenarios", tags=["scenarios"])


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "SalesBoost API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
