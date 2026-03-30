"""Tests for otel_tracing.node_span async context manager."""
import pytest
from app.observability.otel_tracing import node_span


async def test_node_span_is_transparent_when_tracing_disabled():
    """node_span must not raise even when OTel is not initialized."""
    result = []
    async with node_span("test_node"):
        result.append("executed")
    assert result == ["executed"]


async def test_node_span_with_attributes_does_not_raise():
    async with node_span("test_node", {"session_id": "s1", "intent": "pricing"}):
        pass  # no exception


async def test_node_span_returns_none_or_span_object():
    """Yielded value is either None (no OTel) or a span — never raises."""
    async with node_span("test_node") as span:
        # span may be None when tracing not initialized — that's fine
        assert span is None or hasattr(span, "set_attribute")


async def test_node_span_propagates_exception():
    """Exceptions inside the block must propagate normally."""
    with pytest.raises(ValueError, match="boom"):
        async with node_span("test_node"):
            raise ValueError("boom")


async def test_node_span_empty_attributes():
    async with node_span("test_node", {}):
        pass


async def test_node_span_none_attributes():
    async with node_span("test_node", None):
        pass
