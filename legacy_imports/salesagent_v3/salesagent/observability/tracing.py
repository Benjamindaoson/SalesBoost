"""Distributed tracing with OpenTelemetry."""
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from salesagent.core.settings import settings


def setup_tracing(app=None) -> trace.Tracer:
    """
    Initialize OpenTelemetry tracing.

    Args:
        app: FastAPI app instance (optional, for auto-instrumentation)

    Returns:
        Tracer instance for manual span creation
    """
    # Create resource with service information
    resource = Resource.create({
        "service.name": settings.app_name,
        "service.version": settings.app_version,
        "deployment.environment": settings.environment,
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter (sends to Jaeger/Zipkin)
    if settings.otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otlp_endpoint,
            insecure=True,  # Use TLS in production
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI
    if app:
        FastAPIInstrumentor.instrument_app(app)

    # Auto-instrument SQLAlchemy
    SQLAlchemyInstrumentor().instrument()

    # Auto-instrument Redis
    RedisInstrumentor().instrument()

    # Return tracer for manual instrumentation
    return trace.get_tracer(__name__)


# Global tracer instance
tracer = trace.get_tracer(__name__)
