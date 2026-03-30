"""
OpenTelemetry distributed tracing for SalesBoost.

When TRACING_ENABLED=true:
- Initializes TracerProvider with OTLP exporter (if OTEL_EXPORTER_OTLP_ENDPOINT set)
- Falls back to ConsoleSpanExporter in development when no endpoint configured
- Instruments FastAPI for automatic HTTP request tracing
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_initialized = False


def init_otel_tracing(
    service_name: str = "salesboost",
    endpoint: Optional[str] = None,
    enabled: bool = True,
) -> bool:
    """
    Initialize OpenTelemetry tracing. Safe to call multiple times; only runs once.

    Args:
        service_name: Service name for traces
        endpoint: OTLP endpoint (e.g. http://localhost:4317). If None, uses env OTEL_EXPORTER_OTLP_ENDPOINT
        enabled: Whether tracing is enabled

    Returns:
        True if tracing was initialized, False otherwise
    """
    global _initialized
    if _initialized or not enabled:
        return _initialized

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME

        resource = Resource.create({SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)

        otel_endpoint = endpoint or __import__("os").environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otel_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                base = otel_endpoint.rstrip("/")
                exporter = OTLPSpanExporter(endpoint=f"{base}/v1/traces")
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info("OpenTelemetry tracing: OTLP HTTP exporter to %s", otel_endpoint)
            except ImportError:
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                    exporter = OTLPSpanExporter(endpoint=otel_endpoint, insecure=True)
                    provider.add_span_processor(BatchSpanProcessor(exporter))
                    logger.info("OpenTelemetry tracing: OTLP gRPC exporter to %s", otel_endpoint)
                except ImportError:
                    logger.warning("OTLP exporter not installed; using console exporter")
                    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        else:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            logger.info("OpenTelemetry tracing: console exporter (set OTEL_EXPORTER_OTLP_ENDPOINT for OTLP)")

        trace.set_tracer_provider(provider)
        _initialized = True
        return True
    except Exception as e:
        logger.warning("OpenTelemetry tracing initialization failed: %s", e)
        return False


def instrument_fastapi(app) -> bool:
    """
    Instrument FastAPI app with OpenTelemetry. Call after app is created.

    Returns:
        True if instrumentation was applied
    """
    if not _initialized:
        return False
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app, excluded_urls="health,live,ready,metrics")
        logger.info("FastAPI instrumented with OpenTelemetry")
        return True
    except Exception as e:
        logger.warning("FastAPI OpenTelemetry instrumentation failed: %s", e)
        return False


def get_tracer(name: str = "salesboost"):
    """Get a tracer for manual spans. Returns no-op tracer if tracing not initialized."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name, "1.0.0")
    except Exception:
        return None


from contextlib import asynccontextmanager
from typing import Any, Dict


@asynccontextmanager
async def node_span(node_name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Async context manager that wraps a workflow node execution in an OTel span.

    Usage::

        async with node_span("coach", {"session_id": sid}):
            result = await _run_coach_logic(state)

    When tracing is disabled or OTel is unavailable the context manager is a
    transparent no-op so callers never need to guard against it.
    """
    tracer = get_tracer("salesboost.workflow")
    if tracer is None:
        yield
        return

    # Enter the OTel span context synchronously; fall back to no-op on failure.
    _ctx = None
    _span = None
    try:
        _ctx = tracer.start_as_current_span(f"node.{node_name}")
        _span = _ctx.__enter__()
        if attributes:
            for k, v in attributes.items():
                try:
                    _span.set_attribute(k, v)
                except Exception:
                    pass
    except Exception as _setup_err:
        logger.debug("[node_span] OTel setup failed for %s: %s", node_name, _setup_err)
        _ctx = None
        _span = None

    try:
        yield _span
    finally:
        if _ctx is not None:
            try:
                _ctx.__exit__(None, None, None)
            except Exception:
                pass
