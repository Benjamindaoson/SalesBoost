"""
模拟运行 API 端点
"""
import logging
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.sales_simulation.scenarios.loader import ScenarioLoader
from app.sales_simulation.runners.single_agent_runner import SingleAgentRunner
from app.sales_simulation.runners.multi_agent_runner import MultiAgentRunner
from app.sales_simulation.evaluation.metrics_calculator import MetricsCalculator

logger = logging.getLogger(__name__)

router = APIRouter()


class SimulationRunRequest(BaseModel):
    """模拟运行请求"""
    scenario_id: str = Field(..., description="场景 ID")
    agent_type: str = Field(default="single", description="Agent 类型：single/multi")
    num_trajectories: int = Field(default=5, ge=1, le=50, description="轨迹数量")
    seed: int = Field(default=42, description="随机种子")


class SimulationRunResponse(BaseModel):
    """模拟运行响应"""
    run_id: str
    status: str
    message: str
    num_trajectories: int


@router.post("/", response_model=SimulationRunResponse)
async def start_simulation_run(request: SimulationRunRequest):
    """
    启动模拟运行
    
    Args:
        request: 运行请求
        
    Returns:
        运行响应
    """
    try:
        # 加载场景
        loader = ScenarioLoader()
        scenario = loader.load_scenario(request.scenario_id)
        
        # 生成运行 ID
        run_id = str(uuid.uuid4())
        
        logger.info(
            f"Starting simulation run: {run_id}, "
            f"scenario={request.scenario_id}, agent_type={request.agent_type}, "
            f"num_trajectories={request.num_trajectories}"
        )
        
        # 选择运行器
        if request.agent_type == "single":
            runner = SingleAgentRunner(scenario)
        elif request.agent_type == "multi":
            runner = MultiAgentRunner(scenario)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown agent_type: {request.agent_type}")
        
        # 异步运行所有轨迹（简化版：顺序执行）
        trajectories = []
        for i in range(request.num_trajectories):
            seed = request.seed + i
            trajectory = await runner.run(run_id, i, seed)
            trajectories.append(trajectory)
        
        # 计算聚合指标
        metrics = MetricsCalculator.calculate_aggregated_metrics(run_id, trajectories)
        
        logger.info(
            f"Simulation run completed: {run_id}, "
            f"success_rate={metrics.success_rate:.2f}, avg_score={metrics.avg_score:.2f}"
        )
        
        # 简化版：直接返回结果（实际应该存储到数据库）
        return SimulationRunResponse(
            run_id=run_id,
            status="completed",
            message=f"Successfully completed {request.num_trajectories} trajectories",
            num_trajectories=len(trajectories),
        )
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Simulation run failed: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.get("/scenarios")
async def list_scenarios():
    """列出所有可用场景"""
    try:
        loader = ScenarioLoader()
        scenario_ids = loader.list_scenario_ids()
        
        return {
            "scenarios": scenario_ids,
            "count": len(scenario_ids),
        }
    except Exception as e:
        logger.error(f"Failed to list scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))




