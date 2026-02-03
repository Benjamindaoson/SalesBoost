"""
Tool Health Check

Monitors tool availability and health status.
"""
import asyncio
import logging
import time
from typing import Dict, Optional
from enum import Enum

from app.tools.registry import ToolRegistry
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enum"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ToolHealthChecker:
    """
    Health checker for tools.

    Performs lightweight health checks on all registered tools.
    """

    def __init__(self, registry: ToolRegistry):
        """
        Initialize health checker.

        Args:
            registry: Tool registry to check
        """
        self._registry = registry
        self._last_check: Dict[str, float] = {}
        self._check_cache: Dict[str, Dict] = {}
        self._cache_ttl = 30.0  # Cache health checks for 30 seconds

    async def check_tool(
        self,
        tool: BaseTool,
        timeout: float = 2.0
    ) -> Dict:
        """
        Check health of a single tool.

        Args:
            tool: Tool to check
            timeout: Timeout for health check

        Returns:
            Health check result
        """
        start_time = time.time()

        try:
            # Check if tool is enabled
            if not tool.enabled:
                return {
                    "tool": tool.name,
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Tool is disabled",
                    "latency_ms": 0,
                    "timestamp": time.time()
                }

            # Perform lightweight health check
            # For now, just verify tool can be instantiated and has required attributes
            health_check_passed = (
                hasattr(tool, 'name') and
                hasattr(tool, 'description') and
                hasattr(tool, 'run') and
                callable(tool.run)
            )

            if health_check_passed:
                latency_ms = round((time.time() - start_time) * 1000, 2)
                return {
                    "tool": tool.name,
                    "status": HealthStatus.HEALTHY,
                    "message": "Tool is operational",
                    "latency_ms": latency_ms,
                    "timestamp": time.time(),
                    "metadata": {
                        "description": tool.description[:100],
                        "allowed_agents": list(tool.allowed_agents) if tool.allowed_agents else []
                    }
                }
            else:
                return {
                    "tool": tool.name,
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Tool missing required attributes",
                    "latency_ms": 0,
                    "timestamp": time.time()
                }

        except asyncio.TimeoutError:
            return {
                "tool": tool.name,
                "status": HealthStatus.DEGRADED,
                "message": f"Health check timed out after {timeout}s",
                "latency_ms": timeout * 1000,
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Health check failed for {tool.name}: {e}")
            return {
                "tool": tool.name,
                "status": HealthStatus.UNHEALTHY,
                "message": f"Health check error: {str(e)}",
                "error": e.__class__.__name__,
                "latency_ms": 0,
                "timestamp": time.time()
            }

    async def check_all_tools(
        self,
        use_cache: bool = True,
        timeout: float = 2.0
    ) -> Dict[str, Dict]:
        """
        Check health of all registered tools.

        Args:
            use_cache: Whether to use cached results
            timeout: Timeout per tool check

        Returns:
            Dictionary mapping tool names to health status
        """
        now = time.time()

        # Check cache
        if use_cache and self._check_cache:
            cache_age = now - self._last_check.get("all", 0)
            if cache_age < self._cache_ttl:
                logger.debug(f"Using cached health check results (age: {cache_age:.1f}s)")
                return self._check_cache

        logger.info("Performing health check on all tools")

        tools = self._registry.list_tools(include_disabled=True)
        results = {}

        # Check all tools concurrently
        tasks = [self.check_tool(tool, timeout) for tool in tools]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in check_results:
            if isinstance(result, Exception):
                logger.error(f"Health check task failed: {result}")
                continue

            tool_name = result["tool"]
            results[tool_name] = result

        # Update cache
        self._check_cache = results
        self._last_check["all"] = now

        return results

    async def get_summary(self) -> Dict:
        """
        Get health check summary.

        Returns:
            Summary with overall status and counts
        """
        results = await self.check_all_tools()

        healthy = sum(1 for r in results.values() if r["status"] == HealthStatus.HEALTHY)
        degraded = sum(1 for r in results.values() if r["status"] == HealthStatus.DEGRADED)
        unhealthy = sum(1 for r in results.values() if r["status"] == HealthStatus.UNHEALTHY)
        total = len(results)

        # Determine overall status
        if unhealthy > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded > 0:
            overall_status = HealthStatus.DEGRADED
        elif healthy == total:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN

        return {
            "status": overall_status,
            "total_tools": total,
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "timestamp": time.time(),
            "tools": results
        }

    def clear_cache(self) -> None:
        """Clear health check cache"""
        self._check_cache.clear()
        self._last_check.clear()
        logger.info("Health check cache cleared")


# Global instance
_health_checker: Optional[ToolHealthChecker] = None


def get_health_checker(registry: ToolRegistry) -> ToolHealthChecker:
    """Get global health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = ToolHealthChecker(registry)
    return _health_checker
