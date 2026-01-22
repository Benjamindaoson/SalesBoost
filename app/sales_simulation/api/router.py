"""
FastAPI 路由定义
"""
from fastapi import APIRouter

from app.sales_simulation.api.endpoints import simulation, evaluation, datasets

# 创建主路由
router = APIRouter()

# 注册子路由
router.include_router(simulation.router, prefix="/run", tags=["simulation-run"])
router.include_router(evaluation.router, prefix="/eval", tags=["simulation-eval"])
router.include_router(datasets.router, prefix="/datasets", tags=["simulation-datasets"])





