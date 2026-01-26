"""
Admin API Endpoints
管理端功能：课程管理、人设管理、系统配置
"""
import logging
from fastapi import APIRouter

from app.api.endpoints.admin_modules import courses, personas, scenarios, evaluation, knowledge, analytics
from app.api.endpoints.experimental import voice, persona_gen, copilot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

router.include_router(courses.router, prefix="/courses", tags=["admin-courses"])
router.include_router(personas.router, prefix="/personas", tags=["admin-personas"])
router.include_router(scenarios.router, prefix="/scenarios", tags=["admin-scenarios"])
router.include_router(evaluation.router, prefix="/evaluation", tags=["admin-evaluation"])
router.include_router(knowledge.router, prefix="/knowledge", tags=["admin-knowledge"])
router.include_router(analytics.router, prefix="/analytics", tags=["admin-analytics"])

# 实验性功能 (挂载在 /admin 下或独立 /experimental)
# 这里为了方便管理，暂时挂载在 admin 下，实际 SaaS 可能开放给用户
router.include_router(voice.router, prefix="/voice", tags=["experimental-voice"])
router.include_router(persona_gen.router, prefix="/persona-gen", tags=["experimental-persona"])
router.include_router(copilot.router, prefix="/copilot", tags=["experimental-copilot"])

# 权限依赖：仅管理员可访问


# --- 课程管理 (Moved to app/api/endpoints/admin/courses.py) ---
# --- 人设管理 (Moved to app/api/endpoints/admin/personas.py) ---
