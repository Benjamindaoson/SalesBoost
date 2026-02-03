"""
Unit tests for Tool Retry Mechanism
====================================

Tests the ToolRetryPolicy and retry integration in ToolExecutor.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.tools.executor import ToolExecutor, ToolRetryPolicy
from app.tools.registry import ToolRegistry
from app.tools.errors import ToolInputError, ToolPermissionError, ToolNotFoundError
from cognitive.errors import TimeoutError


class TestToolRetryPolicy:
    """Test ToolRetryPolicy class"""

    def test_init_default_values(self):
        """Test default initialization"""
        policy = ToolRetryPolicy()
        assert policy.max_retries == 3
        assert policy.base_delay == 1.0

    def test_init_custom_values(self):
        """Test custom initialization"""
        policy = ToolRetryPolicy(max_retries=5, base_delay=2.0)
        assert policy.max_retries == 5
        assert policy.base_delay == 2.0

    def test_should_retry_non_retryable_errors(self):
        """Test that non-retryable errors return False"""
        policy = ToolRetryPolicy()

        # Non-retryable errors
        assert policy.should_retry(ToolInputError("invalid"), 0) is False
        assert policy.should_retry(ToolPermissionError("forbidden"), 0) is False
        assert policy.should_retry(ToolNotFoundError("not found"), 0) is False

    def test_should_retry_retryable_errors(self):
        """Test that retryable errors return True within max_retries"""
        policy = ToolRetryPolicy(max_retries=3)

        # Retryable errors
        assert policy.should_retry(TimeoutError("timeout"), 0) is True
        assert policy.should_retry(ConnectionError("connection"), 1) is True
        assert policy.should_retry(OSError("os error"), 2) is True

    def test_should_retry_exceeds_max_retries(self):
        """Test that retry returns False when max_retries exceeded"""
        policy = ToolRetryPolicy(max_retries=3)

        # Attempt 3 is the last retry (0, 1, 2, 3 = 4 total attempts)
        assert policy.should_retry(TimeoutError("timeout"), 3) is False
        assert policy.should_retry(TimeoutError("timeout"), 4) is False

    def test_get_delay_exponential_backoff(self):
        """Test exponential backoff calculation"""
        policy = ToolRetryPolicy(base_delay=1.0)

        assert policy.get_delay(0) == 1.0  # 1.0 * 2^0
        assert policy.get_delay(1) == 2.0  # 1.0 * 2^1
        assert policy.get_delay(2) == 4.0  # 1.0 * 2^2
        assert policy.get_delay(3) == 8.0  # 1.0 * 2^3

    def test_get_delay_custom_base(self):
        """Test exponential backoff with custom base delay"""
        policy = ToolRetryPolicy(base_delay=0.5)

        assert policy.get_delay(0) == 0.5  # 0.5 * 2^0
        assert policy.get_delay(1) == 1.0  # 0.5 * 2^1
        assert policy.get_delay(2) == 2.0  # 0.5 * 2^2


class TestToolExecutorRetry:
    """Test retry integration in ToolExecutor"""

    @pytest.fixture
    def mock_registry(self):
        """Create mock registry"""
        registry = Mock(spec=ToolRegistry)
        return registry

    @pytest.fixture
    def mock_tool(self):
        """Create mock tool"""
        tool = AsyncMock()
        tool.run = AsyncMock()
        return tool

    @pytest.mark.asyncio
    async def test_executor_init_with_retry_enabled(self, mock_registry):
        """Test executor initializes retry policy when enabled"""
        with patch('app.tools.executor.get_settings') as mock_settings:
            mock_settings.return_value.TOOL_RETRY_ENABLED = True
            mock_settings.return_value.TOOL_RETRY_MAX_ATTEMPTS = 5
            mock_settings.return_value.TOOL_RETRY_BASE_DELAY = 2.0

            executor = ToolExecutor(registry=mock_registry)

            assert executor._retry_policy is not None
            assert executor._retry_policy.max_retries == 5
            assert executor._retry_policy.base_delay == 2.0

    @pytest.mark.asyncio
    async def test_executor_init_with_retry_disabled(self, mock_registry):
        """Test executor doesn't initialize retry policy when disabled"""
        with patch('app.tools.executor.get_settings') as mock_settings:
            mock_settings.return_value.TOOL_RETRY_ENABLED = False

            executor = ToolExecutor(registry=mock_registry)

            assert executor._retry_policy is None

    @pytest.mark.asyncio
    async def test_executor_init_with_custom_retry_policy(self, mock_registry):
        """Test executor accepts custom retry policy"""
        custom_policy = ToolRetryPolicy(max_retries=10, base_delay=0.5)
        executor = ToolExecutor(registry=mock_registry, retry_policy=custom_policy)

        assert executor._retry_policy is custom_policy
        assert executor._retry_policy.max_retries == 10

    @pytest.mark.asyncio
    async def test_successful_execution_no_retry(self, mock_registry, mock_tool):
        """Test successful execution doesn't trigger retry"""
        mock_registry.get_tool.return_value = mock_tool
        mock_tool.run.return_value = {"data": "success"}

        retry_policy = ToolRetryPolicy(max_retries=3, base_delay=0.1)
        executor = ToolExecutor(registry=mock_registry, retry_policy=retry_policy)

        with patch('app.tools.executor.record_tool_execution'):
            with patch('app.tools.executor.record_retry_attempt') as mock_retry_metric:
                result = await executor.execute(
                    name="test_tool",
                    payload={"query": "test"},
                    caller_role="coach"
                )

                assert result["ok"] is True
                assert result["result"] == {"data": "success"}
                assert result["audit"]["retry_count"] == 0
                assert mock_tool.run.call_count == 1
                assert mock_retry_metric.call_count == 0

    @pytest.mark.asyncio
    async def test_timeout_with_successful_retry(self, mock_registry, mock_tool):
        """Test timeout error triggers retry and succeeds"""
        mock_registry.get_tool.return_value = mock_tool

        # First call times out, second succeeds
        mock_tool.run.side_effect = [
            TimeoutError("timeout"),
            {"data": "success"}
        ]

        retry_policy = ToolRetryPolicy(max_retries=3, base_delay=0.01)
        executor = ToolExecutor(registry=mock_registry, retry_policy=retry_policy)

        with patch('app.tools.executor.record_tool_execution'):
            with patch('app.tools.executor.record_retry_attempt') as mock_retry_metric:
                result = await executor.execute(
                    name="test_tool",
                    payload={"query": "test"},
                    caller_role="coach"
                )

                assert result["ok"] is True
                assert result["result"] == {"data": "success"}
                assert result["audit"]["retry_count"] == 1
                assert mock_tool.run.call_count == 2
                assert mock_retry_metric.call_count == 1
                mock_retry_metric.assert_called_with(tool_name="test_tool", attempt_number=1)

    @pytest.mark.asyncio
    async def test_multiple_retries_before_success(self, mock_registry, mock_tool):
        """Test multiple retries before success"""
        mock_registry.get_tool.return_value = mock_tool

        # Fail twice, then succeed
        mock_tool.run.side_effect = [
            TimeoutError("timeout 1"),
            ConnectionError("connection error"),
            {"data": "success"}
        ]

        retry_policy = ToolRetryPolicy(max_retries=3, base_delay=0.01)
        executor = ToolExecutor(registry=mock_registry, retry_policy=retry_policy)

        with patch('app.tools.executor.record_tool_execution'):
            with patch('app.tools.executor.record_retry_attempt') as mock_retry_metric:
                result = await executor.execute(
                    name="test_tool",
                    payload={"query": "test"},
                    caller_role="coach"
                )

                assert result["ok"] is True
                assert result["result"] == {"data": "success"}
                assert result["audit"]["retry_count"] == 2
                assert mock_tool.run.call_count == 3
                assert mock_retry_metric.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, mock_registry, mock_tool):
        """Test that execution fails after max retries"""
        mock_registry.get_tool.return_value = mock_tool

        # Always timeout
        mock_tool.run.side_effect = TimeoutError("timeout")

        retry_policy = ToolRetryPolicy(max_retries=2, base_delay=0.01)
        executor = ToolExecutor(registry=mock_registry, retry_policy=retry_policy)

        with patch('app.tools.executor.record_tool_execution'):
            with patch('app.tools.executor.record_retry_attempt') as mock_retry_metric:
                result = await executor.execute(
                    name="test_tool",
                    payload={"query": "test"},
                    caller_role="coach"
                )

                assert result["ok"] is False
                assert result["error"]["code"] == "TOOL_TIMEOUT"
                assert result["audit"]["retry_count"] == 2
                # Initial attempt + 2 retries = 3 total calls
                assert mock_tool.run.call_count == 3
                assert mock_retry_metric.call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_error_no_retry(self, mock_registry, mock_tool):
        """Test that non-retryable errors don't trigger retry"""
        mock_registry.get_tool.return_value = mock_tool
        mock_tool.run.side_effect = ToolInputError("invalid input")

        retry_policy = ToolRetryPolicy(max_retries=3, base_delay=0.01)
        executor = ToolExecutor(registry=mock_registry, retry_policy=retry_policy)

        with patch('app.tools.executor.record_tool_execution'):
            with patch('app.tools.executor.record_retry_attempt') as mock_retry_metric:
                result = await executor.execute(
                    name="test_tool",
                    payload={"query": "test"},
                    caller_role="coach"
                )

                assert result["ok"] is False
                assert result["error"]["code"] == "TOOL_INPUT_INVALID"
                assert result["audit"]["retry_count"] == 0
                assert mock_tool.run.call_count == 1
                assert mock_retry_metric.call_count == 0

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, mock_registry, mock_tool):
        """Test that exponential backoff delays are applied"""
        mock_registry.get_tool.return_value = mock_tool

        # Fail twice, then succeed
        mock_tool.run.side_effect = [
            TimeoutError("timeout 1"),
            TimeoutError("timeout 2"),
            {"data": "success"}
        ]

        retry_policy = ToolRetryPolicy(max_retries=3, base_delay=0.1)
        executor = ToolExecutor(registry=mock_registry, retry_policy=retry_policy)

        with patch('app.tools.executor.record_tool_execution'):
            with patch('app.tools.executor.record_retry_attempt'):
                start_time = asyncio.get_event_loop().time()

                result = await executor.execute(
                    name="test_tool",
                    payload={"query": "test"},
                    caller_role="coach"
                )

                elapsed = asyncio.get_event_loop().time() - start_time

                assert result["ok"] is True
                # Should have delays: 0.1s (first retry) + 0.2s (second retry) = 0.3s minimum
                assert elapsed >= 0.3
                assert result["audit"]["retry_count"] == 2

    @pytest.mark.asyncio
    async def test_cache_hit_no_retry(self, mock_registry, mock_tool):
        """Test that cache hits don't trigger retry logic"""
        mock_registry.get_tool.return_value = mock_tool

        retry_policy = ToolRetryPolicy(max_retries=3, base_delay=0.01)
        executor = ToolExecutor(registry=mock_registry, retry_policy=retry_policy)

        # Mock cache to return a hit
        with patch.object(executor._cache, 'get', return_value=("cache_key", {"data": "cached"})):
            with patch('app.tools.executor.record_tool_execution'):
                with patch('app.tools.executor.record_retry_attempt') as mock_retry_metric:
                    result = await executor.execute(
                        name="test_tool",
                        payload={"query": "test"},
                        caller_role="coach"
                    )

                    assert result["ok"] is True
                    assert result["cached"] is True
                    assert result["result"] == {"data": "cached"}
                    assert result["audit"]["retry_count"] == 0
                    assert mock_tool.run.call_count == 0
                    assert mock_retry_metric.call_count == 0
