"""
Tool Health Check API Endpoint
"""
from fastapi import APIRouter
from typing import Dict

from app.tools.registry import build_default_registry
from app.tools.health_check import get_health_checker

router = APIRouter()


@router.get("/health/tools")
async def get_tools_health() -> Dict:
    """
    Get health status of all tools.

    Returns comprehensive health check results for all registered tools.
    """
    registry = build_default_registry()
    health_checker = get_health_checker(registry)

    return await health_checker.get_summary()


@router.get("/health/tools/{tool_name}")
async def get_tool_health(tool_name: str) -> Dict:
    """
    Get health status of a specific tool.

    Args:
        tool_name: Name of the tool to check

    Returns:
        Health check result for the specified tool
    """
    registry = build_default_registry()
    health_checker = get_health_checker(registry)

    results = await health_checker.check_all_tools()

    if tool_name not in results:
        return {
            "tool": tool_name,
            "status": "unknown",
            "message": f"Tool '{tool_name}' not found"
        }

    return results[tool_name]


@router.post("/health/tools/refresh")
async def refresh_health_check() -> Dict:
    """
    Force refresh of health check cache.

    Returns:
        Updated health check summary
    """
    registry = build_default_registry()
    health_checker = get_health_checker(registry)

    # Clear cache to force fresh check
    health_checker.clear_cache()

    return await health_checker.get_summary()
