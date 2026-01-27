"""Admin API Endpoints."""
import logging

from fastapi import APIRouter, Depends

from api.deps import audit_access, require_admin
from api.endpoints.admin_modules import analytics, courses, evaluation, knowledge, personas, scenarios

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin), Depends(audit_access)])

router.include_router(courses.router, prefix="/courses", tags=["admin-courses"])
router.include_router(personas.router, prefix="/personas", tags=["admin-personas"])
router.include_router(scenarios.router, prefix="/scenarios", tags=["admin-scenarios"])
router.include_router(evaluation.router, prefix="/evaluation", tags=["admin-evaluation"])
router.include_router(knowledge.router, prefix="/knowledge", tags=["admin-knowledge"])
router.include_router(analytics.router, prefix="/analytics", tags=["admin-analytics"])

# Optional experimental routes
try:
    from api.endpoints.experimental import copilot, persona_gen, voice

    router.include_router(voice.router, prefix="/voice", tags=["experimental-voice"])
    router.include_router(persona_gen.router, prefix="/persona-gen", tags=["experimental-persona"])
    router.include_router(copilot.router, prefix="/copilot", tags=["experimental-copilot"])
except Exception as exc:
    logger.warning("Experimental routers unavailable: %s", exc)
