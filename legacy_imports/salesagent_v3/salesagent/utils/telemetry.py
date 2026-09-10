"""OpenTelemetry helpers — Span/Trace utilities for every agent node."""
from __future__ import annotations

import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Generator

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

from salesagent.core.settings import settings

# ── Tracer Setup ─────────────────────────────────────────────────────────────

_tracer_provider: TracerProvider | None = None


def setup_telemetry() -> None:
    global _tracer_provider
    resource = Resource.create(
        {
            "service.name": settings.app_name,
            "service.version": settings.app_version,
            "deployment.environment": settings.environment,
        }
    )
    _tracer_provider = TracerProvider(resource=resource)

    # Always add console exporter in dev; OTLP if configured
    _tracer_provider.add_span_processor(
        BatchSpanProcessor(ConsoleSpanExporter() if settings.debug else ConsoleSpanExporter())
    )

    if settings.otel_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            _tracer_provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_endpoint))
            )
        except ImportError:
            pass

    trace.set_tracer_provider(_tracer_provider)


def get_tracer(name: str = "salesagent") -> trace.Tracer:
    return trace.get_tracer(name)


# ── Span Helpers ─────────────────────────────────────────────────────────────

@contextmanager
def span(name: str, attributes: dict[str, Any] | None = None) -> Generator[trace.Span, None, None]:
    """Sync span context manager."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as s:
        if attributes:
            for k, v in attributes.items():
                s.set_attribute(k, str(v))
        yield s


@asynccontextmanager
async def async_span(
    name: str, attributes: dict[str, Any] | None = None
) -> AsyncGenerator[trace.Span, None]:
    """Async span context manager."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as s:
        if attributes:
            for k, v in attributes.items():
                s.set_attribute(k, str(v))
        yield s


class AgentNodeTimer:
    """Context manager that records node latency + token counts as OTel attributes."""

    def __init__(self, node_name: str, model: str = "", session_id: str = "") -> None:
        self.node_name = node_name
        self.model = model
        self.session_id = session_id
        self._start: float = 0.0
        self._span: trace.Span | None = None

    def __enter__(self) -> "AgentNodeTimer":
        self._start = time.perf_counter()
        tracer = get_tracer()
        self._ctx = tracer.start_as_current_span(f"node.{self.node_name}")
        self._span = self._ctx.__enter__()
        if self._span:
            self._span.set_attribute("node.name", self.node_name)
            self._span.set_attribute("model.name", self.model)
            self._span.set_attribute("session.id", self.session_id)
        return self

    def set_tokens(self, input_tokens: int, output_tokens: int) -> None:
        if self._span:
            self._span.set_attribute("llm.input_tokens", input_tokens)
            self._span.set_attribute("llm.output_tokens", output_tokens)

    def __exit__(self, *args: Any) -> None:
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        if self._span:
            self._span.set_attribute("node.latency_ms", round(elapsed_ms, 2))
        if self._ctx:
            self._ctx.__exit__(*args)
