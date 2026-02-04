"""
MCP Service Mesh - MCP服务网格

分布式MCP节点网络，支持：
1. 节点注册和发现
2. 智能路由（基于延迟、负载、成本、质量）
3. 负载均衡
4. 故障转移
5. 健康检查

Author: Claude (Anthropic)
Version: 2.0
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class NodeStatus(str, Enum):
    """节点状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class RoutingStrategy(str, Enum):
    """路由策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_LATENCY = "least_latency"
    LEAST_LOAD = "least_load"
    LEAST_COST = "least_cost"
    HIGHEST_QUALITY = "highest_quality"
    WEIGHTED = "weighted"  # 综合考虑多个因素


@dataclass
class NodeMetrics:
    """节点指标"""
    avg_latency: float = 0.0  # 平均延迟（秒）
    current_load: int = 0  # 当前负载（并发请求数）
    max_load: int = 100  # 最大负载
    success_rate: float = 1.0  # 成功率
    avg_cost: float = 0.0  # 平均成本
    total_requests: int = 0
    failed_requests: int = 0
    last_updated: float = field(default_factory=time.time)


@dataclass
class MCPNode:
    """MCP节点"""
    node_id: str
    name: str
    endpoint: str  # URL or connection string
    capabilities: Set[str]  # 节点能力
    status: NodeStatus = NodeStatus.ONLINE
    metrics: NodeMetrics = field(default_factory=NodeMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # 优先级（越高越优先）
    cost_per_request: float = 0.0  # 每次请求成本
    quality_score: float = 1.0  # 质量分数（0-1）

    def is_available(self) -> bool:
        """检查节点是否可用"""
        if self.status != NodeStatus.ONLINE:
            return False

        # 检查负载
        if self.metrics.current_load >= self.metrics.max_load:
            return False

        # 检查成功率
        if self.metrics.success_rate < 0.5:
            return False

        return True

    def get_score(self, strategy: RoutingStrategy) -> float:
        """
        根据路由策略计算节点分数（越高越好）

        Args:
            strategy: 路由策略

        Returns:
            分数（0-1）
        """
        if strategy == RoutingStrategy.LEAST_LATENCY:
            # 延迟越低越好
            return 1.0 / (1.0 + self.metrics.avg_latency)

        elif strategy == RoutingStrategy.LEAST_LOAD:
            # 负载越低越好
            load_ratio = self.metrics.current_load / max(self.metrics.max_load, 1)
            return 1.0 - load_ratio

        elif strategy == RoutingStrategy.LEAST_COST:
            # 成本越低越好
            return 1.0 / (1.0 + self.cost_per_request)

        elif strategy == RoutingStrategy.HIGHEST_QUALITY:
            # 质量越高越好
            return self.quality_score * self.metrics.success_rate

        elif strategy == RoutingStrategy.WEIGHTED:
            # 综合评分
            latency_score = 1.0 / (1.0 + self.metrics.avg_latency)
            load_score = 1.0 - (self.metrics.current_load / max(self.metrics.max_load, 1))
            cost_score = 1.0 / (1.0 + self.cost_per_request)
            quality_score = self.quality_score * self.metrics.success_rate

            # 加权平均
            return (
                latency_score * 0.3
                + load_score * 0.2
                + cost_score * 0.2
                + quality_score * 0.3
            )

        else:
            return 1.0


class MCPMesh:
    """
    MCP服务网格

    管理分布式MCP节点网络，提供智能路由和负载均衡。

    Usage:
        mesh = MCPMesh()

        # 注册节点
        await mesh.register_node(
            node_id="salesboost-primary",
            name="SalesBoost Primary",
            endpoint="http://localhost:8100",
            capabilities={"sales", "crm", "knowledge"}
        )

        await mesh.register_node(
            node_id="salesboost-intel",
            name="SalesBoost Intelligence",
            endpoint="http://localhost:8101",
            capabilities={"market_research", "competitor_analysis"}
        )

        # 调用能力（自动路由到最佳节点）
        result = await mesh.call_capability(
            capability="market_research",
            method="research_company",
            params={"company": "Acme Corp"},
            strategy=RoutingStrategy.WEIGHTED
        )

        # 获取网格状态
        status = mesh.get_mesh_status()
    """

    def __init__(
        self,
        health_check_interval: float = 30.0,
        default_strategy: RoutingStrategy = RoutingStrategy.WEIGHTED,
    ):
        """
        Initialize mesh

        Args:
            health_check_interval: Health check interval in seconds
            default_strategy: Default routing strategy
        """
        self.nodes: Dict[str, MCPNode] = {}
        self.capability_index: Dict[str, Set[str]] = {}  # capability -> node_ids
        self.health_check_interval = health_check_interval
        self.default_strategy = default_strategy

        # Round-robin counters
        self._round_robin_counters: Dict[str, int] = {}

        # Health check task
        self._health_check_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start mesh (health checks, etc.)"""
        logger.info("Starting MCP Mesh")
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop(self):
        """Stop mesh"""
        logger.info("Stopping MCP Mesh")
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

    async def register_node(
        self,
        node_id: str,
        name: str,
        endpoint: str,
        capabilities: Set[str],
        priority: int = 0,
        cost_per_request: float = 0.0,
        quality_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a node

        Args:
            node_id: Unique node ID
            name: Node name
            endpoint: Node endpoint
            capabilities: Set of capabilities
            priority: Priority (higher = more preferred)
            cost_per_request: Cost per request
            quality_score: Quality score (0-1)
            metadata: Additional metadata
        """
        node = MCPNode(
            node_id=node_id,
            name=name,
            endpoint=endpoint,
            capabilities=capabilities,
            priority=priority,
            cost_per_request=cost_per_request,
            quality_score=quality_score,
            metadata=metadata or {},
        )

        self.nodes[node_id] = node

        # Update capability index
        for capability in capabilities:
            if capability not in self.capability_index:
                self.capability_index[capability] = set()
            self.capability_index[capability].add(node_id)

        logger.info(
            f"Registered node: {node_id} with capabilities: {capabilities}"
        )

    async def unregister_node(self, node_id: str):
        """Unregister a node"""
        if node_id not in self.nodes:
            return

        node = self.nodes[node_id]

        # Remove from capability index
        for capability in node.capabilities:
            if capability in self.capability_index:
                self.capability_index[capability].discard(node_id)

        del self.nodes[node_id]

        logger.info(f"Unregistered node: {node_id}")

    def discover_nodes(
        self, capability: Optional[str] = None, status: Optional[NodeStatus] = None
    ) -> List[MCPNode]:
        """
        Discover nodes

        Args:
            capability: Filter by capability
            status: Filter by status

        Returns:
            List of matching nodes
        """
        nodes = list(self.nodes.values())

        if capability:
            node_ids = self.capability_index.get(capability, set())
            nodes = [n for n in nodes if n.node_id in node_ids]

        if status:
            nodes = [n for n in nodes if n.status == status]

        return nodes

    async def call_capability(
        self,
        capability: str,
        method: str,
        params: Dict[str, Any],
        strategy: Optional[RoutingStrategy] = None,
        timeout: float = 30.0,
        retry: bool = True,
        max_retries: int = 3,
    ) -> Any:
        """
        Call a capability (automatically routes to best node)

        Args:
            capability: Capability name
            method: Method to call
            params: Method parameters
            strategy: Routing strategy (uses default if None)
            timeout: Timeout in seconds
            retry: Whether to retry on failure
            max_retries: Maximum retry attempts

        Returns:
            Result from node

        Raises:
            ValueError: If no nodes available
            RuntimeError: If all attempts failed
        """
        strategy = strategy or self.default_strategy

        for attempt in range(max_retries if retry else 1):
            try:
                # Select node
                node = await self._select_node(capability, strategy)

                if not node:
                    raise ValueError(f"No available nodes for capability: {capability}")

                # Call node
                result = await self._call_node(node, method, params, timeout)

                # Update metrics (success)
                await self._update_metrics(node, success=True, latency=0.0)

                return result

            except Exception as e:
                logger.warning(
                    f"Call to node failed (attempt {attempt + 1}/{max_retries}): {e}"
                )

                # Update metrics (failure)
                if node:
                    await self._update_metrics(node, success=False, latency=0.0)

                if not retry or attempt == max_retries - 1:
                    raise

                # Wait before retry
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(f"All attempts failed for capability: {capability}")

    async def _select_node(
        self, capability: str, strategy: RoutingStrategy
    ) -> Optional[MCPNode]:
        """
        Select best node for capability

        Args:
            capability: Capability name
            strategy: Routing strategy

        Returns:
            Selected node or None
        """
        # Get candidate nodes
        candidates = self.discover_nodes(capability=capability)

        # Filter available nodes
        available = [n for n in candidates if n.is_available()]

        if not available:
            logger.warning(f"No available nodes for capability: {capability}")
            return None

        # Select based on strategy
        if strategy == RoutingStrategy.ROUND_ROBIN:
            # Round-robin
            if capability not in self._round_robin_counters:
                self._round_robin_counters[capability] = 0

            idx = self._round_robin_counters[capability] % len(available)
            self._round_robin_counters[capability] += 1

            return available[idx]

        else:
            # Score-based selection
            scored = [(n, n.get_score(strategy)) for n in available]
            scored.sort(key=lambda x: x[1], reverse=True)

            # Select best node
            return scored[0][0]

    async def _call_node(
        self, node: MCPNode, method: str, params: Dict[str, Any], timeout: float
    ) -> Any:
        """
        Call a node

        Args:
            node: Node to call
            method: Method name
            params: Parameters
            timeout: Timeout

        Returns:
            Result
        """
        import time

        start_time = time.time()

        # Increment load
        node.metrics.current_load += 1

        try:
            # TODO: Actual HTTP/RPC call to node
            # For now, simulate
            await asyncio.sleep(0.1)  # Simulate network latency

            result = {
                "success": True,
                "result": f"Called {method} on {node.name}",
                "node_id": node.node_id,
            }

            latency = time.time() - start_time

            # Update metrics
            await self._update_metrics(node, success=True, latency=latency)

            return result

        except Exception as e:
            latency = time.time() - start_time
            await self._update_metrics(node, success=False, latency=latency)
            raise

        finally:
            # Decrement load
            node.metrics.current_load = max(0, node.metrics.current_load - 1)

    async def _update_metrics(
        self, node: MCPNode, success: bool, latency: float
    ):
        """Update node metrics"""
        metrics = node.metrics

        # Update counters
        metrics.total_requests += 1
        if not success:
            metrics.failed_requests += 1

        # Update success rate (exponential moving average)
        alpha = 0.1
        current_success = 1.0 if success else 0.0
        metrics.success_rate = (
            alpha * current_success + (1 - alpha) * metrics.success_rate
        )

        # Update latency (exponential moving average)
        if latency > 0:
            metrics.avg_latency = alpha * latency + (1 - alpha) * metrics.avg_latency

        metrics.last_updated = time.time()

    async def _health_check_loop(self):
        """Periodic health check"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _health_check(self):
        """Check health of all nodes"""
        for node in self.nodes.values():
            try:
                # TODO: Actual health check (ping node)
                # For now, check metrics

                # Mark as degraded if success rate is low
                if node.metrics.success_rate < 0.7:
                    node.status = NodeStatus.DEGRADED
                    logger.warning(
                        f"Node {node.node_id} degraded: "
                        f"success_rate={node.metrics.success_rate:.2f}"
                    )
                else:
                    node.status = NodeStatus.ONLINE

            except Exception as e:
                logger.error(f"Health check failed for {node.node_id}: {e}")
                node.status = NodeStatus.OFFLINE

    def get_mesh_status(self) -> Dict[str, Any]:
        """Get mesh status"""
        total_nodes = len(self.nodes)
        online_nodes = sum(1 for n in self.nodes.values() if n.status == NodeStatus.ONLINE)
        total_requests = sum(n.metrics.total_requests for n in self.nodes.values())
        total_failures = sum(n.metrics.failed_requests for n in self.nodes.values())

        return {
            "total_nodes": total_nodes,
            "online_nodes": online_nodes,
            "offline_nodes": total_nodes - online_nodes,
            "total_requests": total_requests,
            "total_failures": total_failures,
            "success_rate": (
                (total_requests - total_failures) / total_requests
                if total_requests > 0
                else 1.0
            ),
            "capabilities": list(self.capability_index.keys()),
            "nodes": [
                {
                    "node_id": n.node_id,
                    "name": n.name,
                    "status": n.status.value,
                    "capabilities": list(n.capabilities),
                    "metrics": {
                        "avg_latency": n.metrics.avg_latency,
                        "current_load": n.metrics.current_load,
                        "success_rate": n.metrics.success_rate,
                        "total_requests": n.metrics.total_requests,
                    },
                }
                for n in self.nodes.values()
            ],
        }


# Example usage
async def example_usage():
    """Example of MCP Mesh usage"""
    mesh = MCPMesh()
    await mesh.start()

    # Register nodes
    await mesh.register_node(
        node_id="salesboost-primary",
        name="SalesBoost Primary",
        endpoint="http://localhost:8100",
        capabilities={"sales", "crm", "knowledge"},
        priority=10,
        cost_per_request=0.01,
        quality_score=0.95,
    )

    await mesh.register_node(
        node_id="salesboost-intel",
        name="SalesBoost Intelligence",
        endpoint="http://localhost:8101",
        capabilities={"market_research", "competitor_analysis"},
        priority=5,
        cost_per_request=0.05,
        quality_score=0.90,
    )

    await mesh.register_node(
        node_id="salesboost-backup",
        name="SalesBoost Backup",
        endpoint="http://localhost:8102",
        capabilities={"sales", "crm"},
        priority=1,
        cost_per_request=0.01,
        quality_score=0.85,
    )

    # Call capability with different strategies
    result = await mesh.call_capability(
        capability="market_research",
        method="research_company",
        params={"company": "Acme Corp"},
        strategy=RoutingStrategy.WEIGHTED,
    )

    print(f"Result: {result}")

    # Get mesh status
    status = mesh.get_mesh_status()
    print(f"Mesh status: {status}")

    await mesh.stop()
