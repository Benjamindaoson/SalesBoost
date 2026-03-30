"""
MCP Orchestrator Enhanced - 增强版智能工具编排器

集成了学习引擎、缓存和重试策略的优化版本。

新增功能：
1. 学习引擎集成 - 使用历史数据推荐工具
2. 智能缓存 - 避免重复执行
3. 指数退避重试 - 更可靠的错误恢复
4. 超时控制 - 防止长时间阻塞
5. 批量学习记录 - 异步非阻塞

Author: Claude (Anthropic)
Version: 3.0
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from ..mcp.orchestrator import (
    ExecutionPlan,
    ExecutionResult,
    MCPOrchestrator,
    ToolCall,
)
from ..mcp.cache_manager import MCPCacheManager
from ..mcp.retry_policy import RetryPolicy, is_retryable_error
from ..mcp.learning_engine import MCPLearningEngine

logger = logging.getLogger(__name__)


class MCPOrchestratorEnhanced(MCPOrchestrator):
    """
    增强版MCP编排器

    在原有基础上增加：
    - 学习引擎集成
    - 智能缓存
    - 重试策略
    - 超时控制
    """

    def __init__(
        self,
        tool_registry,
        tool_executor,
        llm_client,
        max_parallel_calls: int = 5,
        learning_engine: Optional[MCPLearningEngine] = None,
        cache_manager: Optional[MCPCacheManager] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        """
        Initialize enhanced orchestrator

        Args:
            tool_registry: Tool registry
            tool_executor: Tool executor
            llm_client: LLM client
            max_parallel_calls: Max parallel calls
            learning_engine: Learning engine (optional)
            cache_manager: Cache manager (optional)
            retry_policy: Retry policy (optional)
        """
        super().__init__(
            tool_registry=tool_registry,
            tool_executor=tool_executor,
            llm_client=llm_client,
            max_parallel_calls=max_parallel_calls,
        )

        self.learning_engine = learning_engine
        self.cache_manager = cache_manager
        self.retry_policy = retry_policy or RetryPolicy(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
        )

        # 批量学习记录队列
        self.learning_queue: asyncio.Queue = asyncio.Queue()
        self.batch_size = 10
        self.flush_interval = 5.0

        # 启动后台批量处理
        if self.learning_engine:
            self._batch_processor_task = asyncio.create_task(
                self._batch_learning_processor()
            )

    async def plan(
        self,
        intent: str,
        context: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """
        AI驱动的工具链规划（集成学习引擎）

        Args:
            intent: User intent
            context: Context
            constraints: Constraints

        Returns:
            Execution plan
        """
        logger.info(f"Planning for intent: {intent}")

        constraints = constraints or {}

        # 使用学习引擎推荐工具
        recommended_tools = []
        if self.learning_engine:
            try:
                recommendations = self.learning_engine.recommend_tools(
                    intent=intent,
                    context=context,
                    max_cost=constraints.get("max_cost"),
                    min_quality=constraints.get("min_quality", 0.7),
                    top_k=10,
                )

                recommended_tools = [t[0] for t in recommendations]

                if recommended_tools:
                    logger.info(
                        f"Learning engine recommended: {', '.join(recommended_tools[:3])}"
                    )

            except Exception as e:
                logger.warning(f"Failed to get recommendations: {e}")

        # Get available tools
        available_tools = self.tool_registry.list_tools()

        # 优先使用推荐的工具
        if recommended_tools:
            # 将推荐的工具排在前面
            tool_descriptions = []

            # 先添加推荐的工具
            for tool_name in recommended_tools:
                tool = next((t for t in available_tools if t.name == tool_name), None)
                if tool:
                    tool_descriptions.append({
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.schema().get("parameters", {}),
                        "recommended": True,
                    })

            # 再添加其他工具
            for tool in available_tools:
                if tool.name not in recommended_tools:
                    tool_descriptions.append({
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.schema().get("parameters", {}),
                        "recommended": False,
                    })
        else:
            tool_descriptions = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.schema().get("parameters", {}),
                }
                for tool in available_tools
            ]

        # Build planning prompt (with recommendations)
        planning_prompt = self._build_planning_prompt_enhanced(
            intent=intent,
            context=context,
            available_tools=tool_descriptions,
            constraints=constraints,
            recommended_tools=recommended_tools,
        )

        # Call LLM
        response = await self.llm_client.chat_completion(
            messages=[{"role": "user", "content": planning_prompt}],
            temperature=0.3,
        )

        # Parse plan
        plan = self._parse_plan_from_llm(response.content, intent)

        # Optimize plan
        plan = await self._optimize_plan(plan, constraints)

        logger.info(
            f"Plan created: {len(plan.tool_calls)} tool calls, "
            f"estimated cost: ${plan.estimated_cost:.3f}"
        )

        return plan

    def _build_planning_prompt_enhanced(
        self,
        intent: str,
        context: Dict[str, Any],
        available_tools: List[Dict],
        constraints: Dict[str, Any],
        recommended_tools: List[str],
    ) -> str:
        """Build enhanced planning prompt with recommendations"""
        tools_str = "\n".join(
            [
                f"- {tool['name']}: {tool['description']}"
                + (" [RECOMMENDED]" if tool.get("recommended") else "")
                for tool in available_tools
            ]
        )

        recommendation_hint = ""
        if recommended_tools:
            recommendation_hint = f"\n\nRecommended tools based on historical performance:\n{', '.join(recommended_tools[:5])}\n"

        prompt = f"""You are an AI tool orchestrator. Plan a sequence of tool calls to accomplish the user's intent.

Intent: {intent}

Context: {context}

Available Tools:
{tools_str}
{recommendation_hint}
Constraints:
- Max cost: ${constraints.get('max_cost', 1.0)}
- Max latency: {constraints.get('max_latency', 30.0)}s

Instructions:
1. Analyze the intent and context
2. Prefer RECOMMENDED tools when applicable (they have proven performance)
3. Select the minimum necessary tools
4. Determine dependencies between tools
5. Optimize for cost and latency
6. Return a JSON plan with this structure:

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

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """
        Execute plan with caching and enhanced error handling

        Args:
            plan: Execution plan

        Returns:
            Execution result
        """
        logger.info(f"Executing plan: {plan.plan_id}")

        # Check cache
        if self.cache_manager:
            cached_result = await self.cache_manager.get_plan_result(
                plan.plan_id,
                plan.intent,
                plan.metadata.get("context", {}),
            )

            if cached_result:
                logger.info(f"Using cached result for plan {plan.plan_id}")
                return ExecutionResult(**cached_result)

        # Execute plan
        start_time = time.time()

        results: Dict[str, Any] = {}
        errors: Dict[str, str] = {}
        total_cost = 0.0

        try:
            # Get execution order
            batches = plan.get_execution_order()

            logger.info(f"Execution plan has {len(batches)} batches")

            # Execute each batch
            for batch_idx, batch in enumerate(batches):
                logger.info(
                    f"Executing batch {batch_idx + 1}/{len(batches)} "
                    f"with {len(batch)} tool calls"
                )

                # Execute batch in parallel
                batch_results = await self._execute_batch_enhanced(batch, results)

                # Update results
                for call_id, result in batch_results.items():
                    if isinstance(result, Exception):
                        errors[call_id] = str(result)
                    else:
                        results[call_id] = result
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

            # Cache result (if successful)
            if self.cache_manager and success:
                await self.cache_manager.set_plan_result(
                    plan.plan_id,
                    plan.intent,
                    plan.metadata.get("context", {}),
                    {
                        "plan_id": execution_result.plan_id,
                        "success": execution_result.success,
                        "results": execution_result.results,
                        "errors": execution_result.errors,
                        "total_cost": execution_result.total_cost,
                        "total_latency": execution_result.total_latency,
                    },
                    ttl=300,  # 5 minutes
                )

            # Queue for batch learning
            if self.learning_engine and success:
                await self._queue_learning_record(plan, execution_result)

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

    async def _execute_batch_enhanced(
        self, batch: List[ToolCall], previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute batch with enhanced error handling"""
        semaphore = asyncio.Semaphore(self.max_parallel_calls)

        async def execute_with_semaphore(call: ToolCall):
            async with semaphore:
                return await self._execute_tool_call_enhanced(call, previous_results)

        tasks = [execute_with_semaphore(call) for call in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {call.call_id: result for call, result in zip(batch, results)}

    async def _execute_tool_call_enhanced(
        self, call: ToolCall, previous_results: Dict[str, Any]
    ) -> Any:
        """
        Execute tool call with caching, retry, and timeout

        Args:
            call: Tool call
            previous_results: Previous results

        Returns:
            Tool result
        """
        logger.info(f"Executing tool: {call.tool_name} (call_id: {call.call_id})")

        # Resolve parameters
        parameters = self._resolve_parameters(call.parameters, previous_results)

        # Check cache
        if self.cache_manager:
            cached_result = await self.cache_manager.get_tool_result(
                call.tool_name,
                parameters,
                {},  # context
            )

            if cached_result:
                logger.info(f"Using cached result for {call.tool_name}")
                return cached_result

        # Execute with retry and timeout
        async def execute_tool():
            try:
                # Add timeout
                result = await asyncio.wait_for(
                    self.tool_executor.execute(
                        name=call.tool_name,
                        payload=parameters,
                        caller_role="orchestrator",
                    ),
                    timeout=call.timeout,
                )

                if result.get("ok"):
                    return result.get("result")
                else:
                    error = result.get("error", {})
                    raise RuntimeError(error.get("message", "Tool execution failed"))

            except asyncio.TimeoutError:
                logger.error(f"Tool {call.tool_name} timed out after {call.timeout}s")
                raise TimeoutError(f"Tool timed out after {call.timeout}s")

        # Execute with retry
        try:
            result = await self.retry_policy.execute_with_retry(
                execute_tool,
                should_retry=is_retryable_error if call.retry_on_failure else None,
            )

            # Cache result
            if self.cache_manager:
                await self.cache_manager.set_tool_result(
                    call.tool_name,
                    parameters,
                    {},
                    result,
                    ttl=600,  # 10 minutes
                )

            logger.info(f"Tool {call.tool_name} succeeded")
            return result

        except Exception as e:
            logger.error(f"Tool {call.tool_name} failed: {e}")
            raise

    async def _queue_learning_record(
        self, plan: ExecutionPlan, result: ExecutionResult
    ):
        """Queue learning record for batch processing"""
        await self.learning_queue.put({
            "plan": plan,
            "result": result,
            "timestamp": time.time(),
        })

    async def _batch_learning_processor(self):
        """Background batch learning processor"""
        batch = []

        while True:
            try:
                # Wait for record or timeout
                record = await asyncio.wait_for(
                    self.learning_queue.get(),
                    timeout=self.flush_interval,
                )

                batch.append(record)

                # Process batch if full
                if len(batch) >= self.batch_size:
                    await self._process_learning_batch(batch)
                    batch = []

            except asyncio.TimeoutError:
                # Timeout - process current batch
                if batch:
                    await self._process_learning_batch(batch)
                    batch = []

            except Exception as e:
                logger.error(f"Batch learning processor error: {e}")

    async def _process_learning_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of learning records"""
        try:
            for record in batch:
                plan = record["plan"]
                result = record["result"]

                # Record each tool execution
                for tool_call in plan.tool_calls:
                    tool_result = result.results.get(tool_call.call_id, {})

                    if isinstance(tool_result, dict):
                        self.learning_engine.record_execution(
                            tool_name=tool_call.tool_name,
                            parameters=tool_call.parameters,
                            context=plan.metadata.get("context", {}),
                            success=tool_call.call_id not in result.errors,
                            latency=tool_result.get("latency", 0.0),
                            cost=tool_result.get("cost", 0.0),
                            quality_score=tool_result.get("quality_score", 0.8),
                        )

                # Record tool combination
                tool_names = [tc.tool_name for tc in plan.tool_calls]
                self.learning_engine.record_combination(
                    tools=tool_names,
                    success=result.success,
                    total_cost=result.total_cost,
                    total_latency=result.total_latency,
                    quality_score=0.8,
                )

            logger.debug(f"Processed learning batch of {len(batch)} records")

        except Exception as e:
            logger.error(f"Failed to process learning batch: {e}")

    async def shutdown(self):
        """Shutdown orchestrator"""
        # Cancel batch processor
        if hasattr(self, "_batch_processor_task"):
            self._batch_processor_task.cancel()
            try:
                await self._batch_processor_task
            except asyncio.CancelledError:
                pass

        # Flush remaining learning records
        if self.learning_engine and not self.learning_queue.empty():
            batch = []
            while not self.learning_queue.empty():
                try:
                    record = self.learning_queue.get_nowait()
                    batch.append(record)
                except asyncio.QueueEmpty:
                    break

            if batch:
                await self._process_learning_batch(batch)

        logger.info("Orchestrator shutdown complete")
