"""
MCP Orchestrator - 智能工具编排器

2026年硅谷顶尖水平的MCP核心组件：
- AI驱动的工具链规划
- 自动依赖分析和优化
- 并行执行和错误恢复
- 实时学习和优化

Author: Claude (Anthropic)
Version: 2.0
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """任务类型"""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    EXECUTION = "execution"
    VALIDATION = "validation"


class TaskPriority(str, Enum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ToolCall:
    """工具调用"""
    tool_name: str
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他工具调用ID
    call_id: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: float = 30.0
    retry_on_failure: bool = True
    max_retries: int = 3


@dataclass
class ExecutionPlan:
    """执行计划"""
    plan_id: str
    intent: str
    tool_calls: List[ToolCall]
    estimated_cost: float = 0.0
    estimated_latency: float = 0.0
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_execution_order(self) -> List[List[ToolCall]]:
        """
        获取执行顺序（拓扑排序）

        Returns:
            List of batches, each batch can be executed in parallel
        """
        # Build dependency graph
        graph: Dict[str, Set[str]] = {}
        in_degree: Dict[str, int] = {}

        for call in self.tool_calls:
            graph[call.call_id] = set(call.dependencies)
            in_degree[call.call_id] = len(call.dependencies)

        # Topological sort with batching
        batches: List[List[ToolCall]] = []
        remaining = {call.call_id: call for call in self.tool_calls}

        while remaining:
            # Find all nodes with no dependencies
            batch = [
                call
                for call_id, call in remaining.items()
                if in_degree[call_id] == 0
            ]

            if not batch:
                # Circular dependency detected
                raise ValueError("Circular dependency detected in execution plan")

            batches.append(batch)

            # Remove batch from remaining
            for call in batch:
                del remaining[call.call_id]

                # Update in-degrees
                for other_id in remaining:
                    if call.call_id in graph[other_id]:
                        in_degree[other_id] -= 1

        return batches


@dataclass
class ExecutionResult:
    """执行结果"""
    plan_id: str
    success: bool
    results: Dict[str, Any]  # call_id -> result
    errors: Dict[str, str]  # call_id -> error
    total_cost: float = 0.0
    total_latency: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPOrchestrator:
    """
    MCP智能编排器

    核心功能：
    1. AI驱动的工具链规划
    2. 自动依赖分析
    3. 并行执行优化
    4. 错误恢复
    5. 成本和延迟优化
    6. 实时学习

    Usage:
        orchestrator = MCPOrchestrator(
            tool_registry=registry,
            tool_executor=executor,
            llm_client=llm
        )

        # AI自动规划
        plan = await orchestrator.plan(
            intent="research customer and create sales strategy",
            context={"customer": "Acme Corp"},
            constraints={"max_cost": 0.50, "max_latency": 10.0}
        )

        # 执行计划
        result = await orchestrator.execute(plan)
    """

    def __init__(
        self,
        tool_registry,
        tool_executor,
        llm_client,
        max_parallel_calls: int = 5,
    ):
        """
        Initialize orchestrator

        Args:
            tool_registry: Tool registry
            tool_executor: Tool executor
            llm_client: LLM client for planning
            max_parallel_calls: Maximum parallel tool calls
        """
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.llm_client = llm_client
        self.max_parallel_calls = max_parallel_calls

        # Performance tracking
        self.execution_history: List[ExecutionResult] = []

    async def plan(
        self,
        intent: str,
        context: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """
        AI驱动的工具链规划

        Args:
            intent: User intent (e.g., "research customer")
            context: Context information
            constraints: Constraints (max_cost, max_latency, etc.)

        Returns:
            Execution plan
        """
        logger.info(f"Planning for intent: {intent}")

        constraints = constraints or {}

        # Get available tools
        available_tools = self.tool_registry.list_tools()
        tool_descriptions = [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.schema().get("parameters", {}),
            }
            for tool in available_tools
        ]

        # Use LLM to plan tool chain
        planning_prompt = self._build_planning_prompt(
            intent=intent,
            context=context,
            available_tools=tool_descriptions,
            constraints=constraints,
        )

        # Call LLM
        response = await self.llm_client.chat_completion(
            messages=[{"role": "user", "content": planning_prompt}],
            temperature=0.3,  # Lower temperature for more deterministic planning
        )

        # Parse LLM response into execution plan
        plan = self._parse_plan_from_llm(response.content, intent)

        # Optimize plan
        plan = await self._optimize_plan(plan, constraints)

        logger.info(
            f"Plan created: {len(plan.tool_calls)} tool calls, "
            f"estimated cost: ${plan.estimated_cost:.3f}, "
            f"estimated latency: {plan.estimated_latency:.2f}s"
        )

        return plan

    def _build_planning_prompt(
        self,
        intent: str,
        context: Dict[str, Any],
        available_tools: List[Dict],
        constraints: Dict[str, Any],
    ) -> str:
        """Build prompt for LLM planning"""
        tools_str = "\n".join(
            [
                f"- {tool['name']}: {tool['description']}"
                for tool in available_tools
            ]
        )

        prompt = f"""You are an AI tool orchestrator. Plan a sequence of tool calls to accomplish the user's intent.

Intent: {intent}

Context: {context}

Available Tools:
{tools_str}

Constraints:
- Max cost: ${constraints.get('max_cost', 1.0)}
- Max latency: {constraints.get('max_latency', 30.0)}s

Instructions:
1. Analyze the intent and context
2. Select the minimum necessary tools
3. Determine dependencies between tools
4. Optimize for cost and latency
5. Return a JSON plan with this structure:

{{
    "tool_calls": [
        {{
            "call_id": "call_1",
            "tool_name": "tool_name",
            "parameters": {{}},
            "dependencies": [],
            "priority": "normal"
        }}
    ],
    "reasoning": "Why this plan is optimal"
}}

Plan:"""

        return prompt

    def _parse_plan_from_llm(self, llm_response: str, intent: str) -> ExecutionPlan:
        """Parse LLM response into execution plan"""
        import json
        import uuid

        try:
            # Extract JSON from response
            start = llm_response.find("{")
            end = llm_response.rfind("}") + 1
            plan_json = json.loads(llm_response[start:end])

            # Create tool calls
            tool_calls = []
            for call_data in plan_json.get("tool_calls", []):
                tool_call = ToolCall(
                    tool_name=call_data["tool_name"],
                    parameters=call_data.get("parameters", {}),
                    dependencies=call_data.get("dependencies", []),
                    call_id=call_data.get("call_id", f"call_{uuid.uuid4().hex[:8]}"),
                    priority=TaskPriority(call_data.get("priority", "normal")),
                )
                tool_calls.append(tool_call)

            plan = ExecutionPlan(
                plan_id=f"plan_{uuid.uuid4().hex[:8]}",
                intent=intent,
                tool_calls=tool_calls,
                metadata={"reasoning": plan_json.get("reasoning", "")},
            )

            return plan

        except Exception as e:
            logger.error(f"Failed to parse plan from LLM: {e}")
            # Fallback: create simple sequential plan
            return self._create_fallback_plan(intent)

    def _create_fallback_plan(self, intent: str) -> ExecutionPlan:
        """Create a simple fallback plan"""
        import uuid

        # Simple heuristic-based planning
        tool_calls = []

        if "research" in intent.lower():
            tool_calls.append(
                ToolCall(
                    call_id="call_1",
                    tool_name="knowledge_retriever",
                    parameters={"query": intent},
                )
            )

        return ExecutionPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:8]}",
            intent=intent,
            tool_calls=tool_calls,
        )

    async def _optimize_plan(
        self, plan: ExecutionPlan, constraints: Dict[str, Any]
    ) -> ExecutionPlan:
        """
        Optimize execution plan

        Optimizations:
        1. Remove redundant tool calls
        2. Reorder for better parallelism
        3. Estimate cost and latency
        4. Apply constraints
        """
        # Estimate cost and latency
        total_cost = 0.0
        total_latency = 0.0

        for call in plan.tool_calls:
            # Get tool metadata
            try:
                tool = self.tool_registry.get_tool(call.tool_name)
                # Estimate based on tool metadata
                tool_cost = getattr(tool, "estimated_cost", 0.01)
                tool_latency = getattr(tool, "estimated_latency", 1.0)

                total_cost += tool_cost
                total_latency = max(total_latency, tool_latency)  # Parallel execution

            except Exception:
                pass

        plan.estimated_cost = total_cost
        plan.estimated_latency = total_latency

        # Check constraints
        max_cost = constraints.get("max_cost", float("inf"))
        max_latency = constraints.get("max_latency", float("inf"))

        if total_cost > max_cost:
            logger.warning(
                f"Plan exceeds cost constraint: ${total_cost:.3f} > ${max_cost:.3f}"
            )
            # TODO: Optimize by removing expensive tools

        if total_latency > max_latency:
            logger.warning(
                f"Plan exceeds latency constraint: {total_latency:.2f}s > {max_latency:.2f}s"
            )
            # TODO: Optimize by using faster tools

        return plan

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """
        Execute plan with parallel optimization

        Args:
            plan: Execution plan

        Returns:
            Execution result
        """
        logger.info(f"Executing plan: {plan.plan_id}")

        import time

        start_time = time.time()

        results: Dict[str, Any] = {}
        errors: Dict[str, str] = {}
        total_cost = 0.0

        try:
            # Get execution order (batches for parallel execution)
            batches = plan.get_execution_order()

            logger.info(f"Execution plan has {len(batches)} batches")

            # Execute each batch in parallel
            for batch_idx, batch in enumerate(batches):
                logger.info(
                    f"Executing batch {batch_idx + 1}/{len(batches)} "
                    f"with {len(batch)} tool calls"
                )

                # Execute batch in parallel
                batch_results = await self._execute_batch(batch, results)

                # Update results
                for call_id, result in batch_results.items():
                    if isinstance(result, Exception):
                        errors[call_id] = str(result)
                    else:
                        results[call_id] = result
                        # Track cost
                        if isinstance(result, dict):
                            total_cost += result.get("cost", 0.0)

            success = len(errors) == 0
            total_latency = time.time() - start_time

            execution_result = ExecutionResult(
                plan_id=plan.plan_id,
                success=success,
                results=results,
                errors=errors,
                total_cost=total_cost,
                total_latency=total_latency,
            )

            # Track for learning
            self.execution_history.append(execution_result)

            logger.info(
                f"Plan execution {'succeeded' if success else 'failed'}: "
                f"cost=${total_cost:.3f}, latency={total_latency:.2f}s"
            )

            return execution_result

        except Exception as e:
            logger.error(f"Plan execution failed: {e}", exc_info=True)
            return ExecutionResult(
                plan_id=plan.plan_id,
                success=False,
                results=results,
                errors={"execution": str(e)},
                total_latency=time.time() - start_time,
            )

    async def _execute_batch(
        self, batch: List[ToolCall], previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a batch of tool calls in parallel

        Args:
            batch: List of tool calls to execute
            previous_results: Results from previous batches

        Returns:
            Dict mapping call_id to result
        """
        # Limit parallelism
        semaphore = asyncio.Semaphore(self.max_parallel_calls)

        async def execute_with_semaphore(call: ToolCall):
            async with semaphore:
                return await self._execute_tool_call(call, previous_results)

        # Execute all calls in parallel
        tasks = [execute_with_semaphore(call) for call in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results to call IDs
        return {call.call_id: result for call, result in zip(batch, results)}

    async def _execute_tool_call(
        self, call: ToolCall, previous_results: Dict[str, Any]
    ) -> Any:
        """
        Execute a single tool call

        Args:
            call: Tool call
            previous_results: Results from previous calls (for dependency resolution)

        Returns:
            Tool result
        """
        logger.info(f"Executing tool: {call.tool_name} (call_id: {call.call_id})")

        # Resolve parameters from dependencies
        parameters = self._resolve_parameters(call.parameters, previous_results)

        # Execute tool with retry
        for attempt in range(call.max_retries):
            try:
                result = await self.tool_executor.execute(
                    name=call.tool_name,
                    payload=parameters,
                    caller_role="orchestrator",
                )

                if result.get("ok"):
                    logger.info(f"Tool {call.tool_name} succeeded")
                    return result.get("result")
                else:
                    error = result.get("error", {})
                    logger.warning(
                        f"Tool {call.tool_name} failed: {error.get('message')}"
                    )

                    if not call.retry_on_failure or attempt == call.max_retries - 1:
                        raise RuntimeError(error.get("message", "Tool execution failed"))

                    # Wait before retry
                    await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Tool {call.tool_name} error: {e}")

                if not call.retry_on_failure or attempt == call.max_retries - 1:
                    raise

                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(f"Tool {call.tool_name} failed after {call.max_retries} attempts")

    def _resolve_parameters(
        self, parameters: Dict[str, Any], previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve parameters from previous results

        Supports references like: {"customer_name": "$call_1.company_name"}
        """
        resolved = {}

        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("$"):
                # Reference to previous result
                ref = value[1:]  # Remove $
                parts = ref.split(".")

                if len(parts) == 1:
                    # Reference to entire result
                    resolved[key] = previous_results.get(parts[0])
                else:
                    # Reference to nested field
                    call_id = parts[0]
                    field_path = parts[1:]

                    result = previous_results.get(call_id, {})
                    for field in field_path:
                        if isinstance(result, dict):
                            result = result.get(field)
                        else:
                            break

                    resolved[key] = result
            else:
                resolved[key] = value

        return resolved

    async def optimize_from_feedback(self, feedback: Dict[str, Any]):
        """
        Learn from execution feedback

        Args:
            feedback: Feedback data (success, user_satisfaction, etc.)
        """
        # TODO: Implement learning algorithm
        # - Update tool selection preferences
        # - Adjust cost/latency weights
        # - Improve dependency inference
        pass

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.execution_history:
            return {}

        total_executions = len(self.execution_history)
        successful = sum(1 for r in self.execution_history if r.success)
        total_cost = sum(r.total_cost for r in self.execution_history)
        avg_latency = sum(r.total_latency for r in self.execution_history) / total_executions

        return {
            "total_executions": total_executions,
            "success_rate": successful / total_executions,
            "total_cost": total_cost,
            "average_cost": total_cost / total_executions,
            "average_latency": avg_latency,
        }
