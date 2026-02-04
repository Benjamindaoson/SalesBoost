from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, Optional, Callable, Awaitable

from app.tools.tool_cache import ToolCache
from app.tools.errors import ToolInputError, ToolNotFoundError, ToolPermissionError
from app.tools.registry import ToolRegistry
from app.tools.rate_limiter import get_rate_limiter
from app.tools.reflection import ReflectionAgent
from app.tools.dependencies import ExecutionContext
from app.cognitive.tools import run_with_timeout
from app.cognitive.errors import TimeoutError
from app.observability.tool_metrics import record_tool_execution, record_retry_attempt
from core.config import get_settings

logger = logging.getLogger(__name__)

# Type alias for tool status callback
ToolStatusCallback = Callable[[Dict[str, Any]], Awaitable[None]]


class RateLimitError(Exception):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str, retry_after: float):
        super().__init__(message)
        self.retry_after = retry_after


class ToolRetryPolicy:
    """
    Retry policy for tool execution with exponential backoff.

    Implements retry logic for transient failures like timeouts and network errors.
    Non-retryable errors (input validation, permissions) fail immediately.
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        Initialize retry policy.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if error is retryable.

        Args:
            error: The exception that occurred
            attempt: Current attempt number (0-indexed)

        Returns:
            True if should retry, False otherwise
        """
        # Non-retryable errors
        non_retryable = (ToolInputError, ToolPermissionError, ToolNotFoundError)
        if isinstance(error, non_retryable):
            return False

        # Retryable errors
        retryable = (TimeoutError, ConnectionError, OSError)
        if isinstance(error, retryable) and attempt < self.max_retries:
            return True

        return False

    def get_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: delay = base_delay * (2 ** attempt)
        return self.base_delay * (2 ** attempt)


class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        timeout: float = 5.0,
        cache: Optional[ToolCache] = None,
        retry_policy: Optional[ToolRetryPolicy] = None,
        reflection_agent: Optional[ReflectionAgent] = None,
        enable_self_correction: bool = True,
    ) -> None:
        self._registry = registry
        self._timeout = timeout
        self._cache = cache or ToolCache()
        settings = get_settings()
        if retry_policy is None and settings.TOOL_RETRY_ENABLED:
            retry_policy = ToolRetryPolicy(
                max_retries=settings.TOOL_RETRY_MAX_ATTEMPTS,
                base_delay=settings.TOOL_RETRY_BASE_DELAY
            )
        self._retry_policy = retry_policy
        self._reflection_agent = reflection_agent or ReflectionAgent()
        self._enable_self_correction = enable_self_correction

    async def execute(
        self,
        name: str,
        payload: Dict[str, Any],
        caller_role: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        status_callback: Optional[ToolStatusCallback] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        ok = False
        result: Any = None
        error: Optional[Dict[str, Any]] = None
        status = "success"
        error_code = None
        cache_hit = False
        cache_key: Optional[str] = None
        retry_count = 0

        if not caller_role and agent_type:
            caller_role = agent_type
        if not caller_role:
            raise ToolInputError("caller_role is required")
        if not tool_call_id:
            tool_call_id = f"auto-{uuid.uuid4().hex}"

        # Check rate limit
        rate_limiter = get_rate_limiter()
        allowed, retry_after = await rate_limiter.check_limit(name)
        if not allowed:
            error_msg = f"Rate limit exceeded for tool '{name}'. Retry after {retry_after:.2f}s"
            logger.warning(error_msg)
            raise RateLimitError(error_msg, retry_after)

        # Emit started event
        if status_callback:
            try:
                await status_callback({
                    "tool_name": name,
                    "status": "started",
                    "tool_call_id": tool_call_id,
                    "caller_role": caller_role
                })
            except Exception as e:
                logger.warning(f"Failed to emit tool started event: {e}")

        # Retry loop
        attempt = 0
        last_exception = None

        while attempt <= (self._retry_policy.max_retries if self._retry_policy else 0):
            try:
                tool = self._registry.get_tool(name, agent_type=caller_role)
                cached = await self._cache.get(name, payload)
                if cached:
                    ok = True
                    status = "cache_hit"
                    result = cached[1]
                    cache_hit = True
                    cache_key = cached[0]
                else:
                    # Set up execution context for dependency injection
                    async with ExecutionContext(
                        context=context,
                        session_id=context.get("session_id") if context else None,
                        user_id=context.get("user_id") if context else None,
                        agent_type=caller_role
                    ):
                        result = await run_with_timeout(tool.run(payload), timeout=self._timeout)
                    ok = True
                    await self._cache.set(name, payload, result)

                # Success - break out of retry loop
                break

            except ToolNotFoundError as exc:
                status = "not_found"
                error_code = "TOOL_NOT_FOUND"
                error = {"type": exc.__class__.__name__, "message": str(exc), "code": error_code}
                last_exception = exc
                break  # Non-retryable
            except ToolPermissionError as exc:
                status = "forbidden"
                error_code = "TOOL_FORBIDDEN"
                error = {"type": exc.__class__.__name__, "message": str(exc), "code": error_code}
                last_exception = exc
                break  # Non-retryable
            except ToolInputError as exc:
                status = "invalid_input"
                error_code = "TOOL_INPUT_INVALID"
                error = {"type": exc.__class__.__name__, "message": str(exc), "code": error_code}
                last_exception = exc
                break  # Non-retryable
            except TimeoutError as exc:
                status = "timeout"
                error_code = "TOOL_TIMEOUT"
                error = {"type": exc.__class__.__name__, "message": str(exc), "code": error_code}
                last_exception = exc
                # Retryable - continue to retry logic below
            except Exception as exc:
                status = "error"
                error_code = "TOOL_EXECUTION_FAILED"
                error = {"type": exc.__class__.__name__, "message": str(exc), "code": error_code}
                last_exception = exc
                # Retryable - continue to retry logic below

            # Check if we should retry
            if self._retry_policy and self._retry_policy.should_retry(last_exception, attempt):
                retry_count += 1
                attempt += 1
                delay = self._retry_policy.get_delay(attempt - 1)

                logger.warning(
                    f"Tool {name} failed (attempt {attempt}), retrying in {delay}s: {last_exception}"
                )

                # Record retry attempt
                record_retry_attempt(tool_name=name, attempt_number=attempt)

                # Wait before retry
                await asyncio.sleep(delay)
            else:
                # No more retries
                break

        latency_ms = round((time.time() - start_time) * 1000, 2)
        audit = {
            "status": status,
            "latency_ms": latency_ms,
            "caller_role": caller_role,
            "tool_call_id": tool_call_id,
            "tool": name,
            "error_code": error_code,
            "retry_count": retry_count,
            "context": context or {},
        }

        # Record metrics
        record_tool_execution(
            tool_name=name,
            status=status,
            latency_ms=latency_ms,
            caller_role=caller_role,
            error_type=error.get("type") if error else None,
            cached=cache_hit
        )

        # Emit completed/failed event
        if status_callback:
            try:
                event_data = {
                    "tool_name": name,
                    "status": "completed" if ok else "failed",
                    "tool_call_id": tool_call_id,
                    "caller_role": caller_role,
                    "latency_ms": latency_ms,
                    "cached": cache_hit,
                    "retry_count": retry_count
                }

                # Add result preview for successful executions
                if ok and result:
                    result_preview = self._generate_result_preview(result)
                    event_data["result_preview"] = result_preview

                # Add error for failed executions
                if not ok and error:
                    event_data["error"] = error.get("message", "Unknown error")
                    event_data["error_code"] = error_code

                await status_callback(event_data)
            except Exception as e:
                logger.warning(f"Failed to emit tool completion event: {e}")

        return {
            "ok": ok,
            "tool": name,
            "tool_call_id": tool_call_id,
            "caller_role": caller_role,
            "result": result,
            "error": error,
            "cached": cache_hit,
            "cache_key": cache_key,
            "audit": audit,
        }

    def _generate_result_preview(self, result: Any, max_length: int = 100) -> str:
        """
        Generate a preview of the tool result for display.

        Args:
            result: Tool execution result
            max_length: Maximum length of preview

        Returns:
            Preview string
        """
        try:
            if isinstance(result, dict):
                # For dict results, show key information
                if "success" in result:
                    if result["success"]:
                        # Show count or summary
                        if "count" in result:
                            return f"Success: {result['count']} items"
                        elif "documents" in result:
                            return f"Found {len(result['documents'])} documents"
                        elif "customer" in result:
                            return f"Customer: {result['customer'].get('name', 'N/A')}"
                        elif "message_id" in result:
                            return f"Sent: {result['message_id']}"
                        else:
                            return "Success"
                    else:
                        return f"Failed: {result.get('error', 'Unknown error')}"
                else:
                    # Generic dict preview
                    preview = str(result)
                    return preview[:max_length] + "..." if len(preview) > max_length else preview
            elif isinstance(result, (list, tuple)):
                return f"List with {len(result)} items"
            elif isinstance(result, str):
                return result[:max_length] + "..." if len(result) > max_length else result
            else:
                preview = str(result)
                return preview[:max_length] + "..." if len(preview) > max_length else preview
        except Exception as e:
            logger.warning(f"Failed to generate result preview: {e}")
            return "Result available"

    async def execute_parallel(
        self,
        tool_calls: list[Dict[str, Any]],
        caller_role: str,
        max_concurrent: Optional[int] = None,
        status_callback: Optional[ToolStatusCallback] = None,
        auto_classify: bool = True,
    ) -> list[Dict[str, Any]]:
        """
        Execute multiple tools in parallel with intelligent read/write classification.

        This method automatically classifies tools as read or write operations:
        - Read operations: Run in parallel for maximum speed
        - Write operations: Run sequentially to avoid conflicts

        Args:
            tool_calls: List of tool call specifications, each containing:
                - name: Tool name
                - payload: Tool payload
                - tool_call_id: Optional tool call ID
                - is_write: Optional explicit write flag (overrides auto-classification)
            caller_role: Caller role for all executions
            max_concurrent: Maximum concurrent executions (default from settings)
            status_callback: Optional callback for status events
            auto_classify: Enable automatic read/write classification (default: True)

        Returns:
            List of execution results in same order as input

        Example:
            results = await executor.execute_parallel([
                {"name": "knowledge_retriever", "payload": {"query": "A"}},  # Read
                {"name": "crm_integration", "payload": {"action": "list"}},  # Read
                {"name": "crm_integration", "payload": {"action": "create"}},  # Write
            ], caller_role="coach")
        """
        settings = get_settings()

        # Check if parallel execution is enabled
        if not settings.TOOL_PARALLEL_ENABLED:
            logger.warning("Parallel execution disabled, falling back to sequential")
            results = []
            for call in tool_calls:
                result = await self.execute(
                    name=call["name"],
                    payload=call["payload"],
                    caller_role=caller_role,
                    tool_call_id=call.get("tool_call_id"),
                    status_callback=status_callback
                )
                results.append(result)
            return results

        # Classify tools as read or write
        if auto_classify:
            read_calls, write_calls = self._classify_tool_calls(tool_calls)
        else:
            # Use explicit is_write flag
            read_calls = [(i, call) for i, call in enumerate(tool_calls) if not call.get("is_write", False)]
            write_calls = [(i, call) for i, call in enumerate(tool_calls) if call.get("is_write", False)]

        logger.info(
            f"Executing {len(tool_calls)} tools: "
            f"{len(read_calls)} read (parallel), {len(write_calls)} write (sequential)"
        )

        # Determine concurrency limit
        if max_concurrent is None:
            max_concurrent = settings.TOOL_PARALLEL_MAX_CONCURRENT

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(call: Dict[str, Any], index: int) -> tuple[int, Dict[str, Any]]:
            """Execute single tool with semaphore"""
            async with semaphore:
                try:
                    result = await self.execute(
                        name=call["name"],
                        payload=call["payload"],
                        caller_role=caller_role,
                        tool_call_id=call.get("tool_call_id"),
                        context=call.get("context"),
                        status_callback=status_callback
                    )
                    return index, result
                except Exception as e:
                    # Return error result instead of raising
                    logger.error(f"Parallel execution failed for {call['name']}: {e}")
                    return index, {
                        "ok": False,
                        "tool": call["name"],
                        "error": {
                            "type": e.__class__.__name__,
                            "message": str(e),
                            "code": "PARALLEL_EXECUTION_FAILED"
                        },
                        "audit": {
                            "status": "error",
                            "error_code": "PARALLEL_EXECUTION_FAILED"
                        }
                    }

        # Execute read operations in parallel
        read_tasks = [
            execute_with_semaphore(call, index)
            for index, call in read_calls
        ]

        read_results = []
        if read_tasks:
            logger.debug(f"Executing {len(read_tasks)} read operations in parallel")
            read_results = await asyncio.gather(*read_tasks)

        # Execute write operations sequentially
        write_results = []
        if write_calls:
            logger.debug(f"Executing {len(write_calls)} write operations sequentially")
            for index, call in write_calls:
                result = await self.execute(
                    name=call["name"],
                    payload=call["payload"],
                    caller_role=caller_role,
                    tool_call_id=call.get("tool_call_id"),
                    context=call.get("context"),
                    status_callback=status_callback
                )
                write_results.append((index, result))

        # Combine and sort results by original index
        all_results = list(read_results) + write_results
        sorted_results = sorted(all_results, key=lambda x: x[0])
        results = [result for _, result in sorted_results]

        # Log summary
        success_count = sum(1 for r in results if r.get("ok", False))
        logger.info(
            f"Parallel execution complete: {success_count}/{len(results)} succeeded"
        )

        return results

    def _classify_tool_calls(
        self,
        tool_calls: list[Dict[str, Any]]
    ) -> tuple[list[tuple[int, Dict[str, Any]]], list[tuple[int, Dict[str, Any]]]]:
        """
        Classify tool calls as read or write operations.

        Classification rules (in priority order):
        1. Explicit is_write flag in tool call takes precedence
        2. Tool's is_side_effect_free attribute (explicit declaration)
        3. Tool name patterns (e.g., "create_", "update_", "delete_")
        4. Payload action field (e.g., {"action": "create"})
        5. Known read-only tools (retriever, search, analysis)
        6. Default: treat as read (safe default)

        Args:
            tool_calls: List of tool call specifications

        Returns:
            (read_calls, write_calls) - each as list of (index, call) tuples
        """
        read_calls = []
        write_calls = []

        # Known read-only tools (fallback for tools without explicit declaration)
        read_only_tools = {
            "knowledge_retriever",
            "competitor_analysis",
            "profile_reader",
            "stage_classifier",
            "price_calculator",
        }

        # Write operation patterns (fallback for pattern-based detection)
        write_patterns = [
            "create", "update", "delete", "remove", "insert",
            "modify", "save", "write", "send", "post", "put"
        ]

        for i, call in enumerate(tool_calls):
            # Check explicit flag first (highest priority)
            if "is_write" in call:
                if call["is_write"]:
                    write_calls.append((i, call))
                else:
                    read_calls.append((i, call))
                continue

            tool_name = call["name"]
            payload = call.get("payload", {})

            # Check tool's explicit is_side_effect_free attribute
            try:
                tool = self._registry.get_tool(tool_name)
                if hasattr(tool, "is_side_effect_free"):
                    if tool.is_side_effect_free:
                        read_calls.append((i, call))
                    else:
                        write_calls.append((i, call))
                    continue
            except Exception:
                # Tool not found or error, continue with fallback methods
                pass

            # Check if known read-only tool
            if tool_name in read_only_tools:
                read_calls.append((i, call))
                continue

            # Check tool name for write patterns
            tool_name_lower = tool_name.lower()
            if any(pattern in tool_name_lower for pattern in write_patterns):
                write_calls.append((i, call))
                continue

            # Check payload action field
            action = payload.get("action", "").lower()
            if action and any(pattern in action for pattern in write_patterns):
                write_calls.append((i, call))
                continue

            # Check payload method field (for REST-like tools)
            method = payload.get("method", "").upper()
            if method in ["POST", "PUT", "PATCH", "DELETE"]:
                write_calls.append((i, call))
                continue

            # Default: treat as read (safe default)
            read_calls.append((i, call))

        return read_calls, write_calls

    async def execute_with_correction(
        self,
        name: str,
        payload: Dict[str, Any],
        caller_role: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        status_callback: Optional[ToolStatusCallback] = None,
        max_corrections: int = 2,
    ) -> Dict[str, Any]:
        """
        Execute tool with automatic self-correction on validation errors.

        This method implements a reflection-based self-correction loop:
        1. Attempt to execute the tool
        2. If validation error occurs, use ReflectionAgent to correct parameters
        3. Retry with corrected parameters
        4. Repeat up to max_corrections times

        Args:
            name: Tool name
            payload: Tool parameters
            caller_role: Caller role
            tool_call_id: Optional tool call ID
            agent_type: Optional agent type
            context: Optional execution context
            status_callback: Optional status callback
            max_corrections: Maximum number of correction attempts (default: 2)

        Returns:
            Execution result with correction metadata

        Example:
            # Original call with invalid parameters
            result = await executor.execute_with_correction(
                name="knowledge_retriever",
                payload={"query": 123},  # Wrong type
                caller_role="coach"
            )
            # Automatically corrects to {"query": "123"} and retries
        """
        if not self._enable_self_correction:
            # Self-correction disabled, fall back to regular execution
            return await self.execute(
                name=name,
                payload=payload,
                caller_role=caller_role,
                tool_call_id=tool_call_id,
                agent_type=agent_type,
                context=context,
                status_callback=status_callback
            )

        correction_attempts = []
        current_payload = payload

        for attempt in range(max_corrections + 1):
            # Attempt execution
            result = await self.execute(
                name=name,
                payload=current_payload,
                caller_role=caller_role,
                tool_call_id=tool_call_id,
                agent_type=agent_type,
                context=context,
                status_callback=status_callback
            )

            # Success - return result
            if result.get("ok", False):
                if correction_attempts:
                    # Add correction metadata to result
                    result["self_correction"] = {
                        "enabled": True,
                        "attempts": len(correction_attempts),
                        "corrections": correction_attempts
                    }
                    logger.info(
                        f"Tool {name} succeeded after {len(correction_attempts)} correction(s)"
                    )
                return result

            # Check if error is correctable
            error = result.get("error", {})
            error_code = error.get("code")

            if error_code != "TOOL_INPUT_INVALID":
                # Non-validation error, cannot correct
                logger.debug(f"Error {error_code} is not correctable, returning failure")
                result["self_correction"] = {
                    "enabled": True,
                    "attempts": len(correction_attempts),
                    "corrections": correction_attempts,
                    "final_error": "Non-correctable error type"
                }
                return result

            # Last attempt failed and no more corrections allowed
            if attempt >= max_corrections:
                logger.warning(
                    f"Tool {name} failed after {max_corrections} correction attempts"
                )
                result["self_correction"] = {
                    "enabled": True,
                    "attempts": len(correction_attempts),
                    "corrections": correction_attempts,
                    "final_error": "Max corrections exceeded"
                }
                return result

            # Attempt correction
            logger.info(
                f"Attempting correction {attempt + 1}/{max_corrections} for tool {name}"
            )

            try:
                # Get tool schema for correction
                tool = self._registry.get_tool(name, agent_type=caller_role or agent_type)
                tool_schema = tool.schema()

                # Use reflection agent to correct parameters
                correction = await self._reflection_agent.correct_tool_call(
                    tool_name=name,
                    original_payload=current_payload,
                    error_message=error.get("message", ""),
                    tool_schema=tool_schema
                )

                if not correction:
                    logger.warning(f"Reflection agent could not correct tool call: {name}")
                    result["self_correction"] = {
                        "enabled": True,
                        "attempts": len(correction_attempts),
                        "corrections": correction_attempts,
                        "final_error": "No correction found"
                    }
                    return result

                # Log correction
                correction_info = {
                    "attempt": attempt + 1,
                    "original_payload": current_payload,
                    "corrected_payload": correction.corrected_payload,
                    "reasoning": correction.correction_reasoning,
                    "confidence": correction.confidence
                }
                correction_attempts.append(correction_info)

                logger.info(
                    f"Correction {attempt + 1}: {correction.correction_reasoning} "
                    f"(confidence: {correction.confidence:.2f})"
                )

                # Update payload for next attempt
                current_payload = correction.corrected_payload

            except Exception as e:
                logger.error(f"Correction attempt failed: {e}")
                result["self_correction"] = {
                    "enabled": True,
                    "attempts": len(correction_attempts),
                    "corrections": correction_attempts,
                    "final_error": f"Correction failed: {str(e)}"
                }
                return result

        # Should not reach here, but return last result as fallback
        result["self_correction"] = {
            "enabled": True,
            "attempts": len(correction_attempts),
            "corrections": correction_attempts,
            "final_error": "Unexpected end of correction loop"
        }
        return result

