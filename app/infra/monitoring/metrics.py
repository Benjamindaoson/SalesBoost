"""
Prometheus Metrics Collection

Collects and exposes metrics for monitoring.

Metrics:
- HTTP request count (by method, endpoint, status)
- HTTP request latency (histogram)
- Active connections (gauge)
- LLM API calls (by provider, model)
- LLM token usage (by provider)
- RAG retrieval count and latency
- Database query count and latency
- Cache hit/miss rate
- Error count (by type)

Usage:
    from app.infra.monitoring import metrics

    # Increment counter
    metrics.http_requests_total.labels(method="GET", endpoint="/api/v1/health", status=200).inc()

    # Observe histogram
    metrics.http_request_duration_seconds.observe(0.123)

    # Set gauge
    metrics.active_connections.set(42)
"""

from prometheus_client import Counter, Histogram, Gauge, Summary, Info
import time
from functools import wraps
from typing import Callable
import logging

logger = logging.getLogger(__name__)

# ==================== HTTP Metrics ====================

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

http_request_size_bytes = Summary(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint']
)

http_response_size_bytes = Summary(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

# ==================== LLM Metrics ====================

llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM API requests',
    ['provider', 'model', 'status']
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM API request latency in seconds',
    ['provider', 'model'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total LLM tokens used',
    ['provider', 'model', 'type']  # type: prompt, completion
)

llm_circuit_breaker_state = Gauge(
    'llm_circuit_breaker_state',
    'LLM circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['provider']
)

# ==================== RAG Metrics ====================

rag_retrieval_total = Counter(
    'rag_retrieval_total',
    'Total RAG retrieval requests',
    ['search_mode', 'status']
)

rag_retrieval_duration_seconds = Histogram(
    'rag_retrieval_duration_seconds',
    'RAG retrieval latency in seconds',
    ['search_mode'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0)
)

rag_documents_retrieved = Histogram(
    'rag_documents_retrieved',
    'Number of documents retrieved',
    buckets=(1, 3, 5, 10, 20, 50, 100)
)

rag_rerank_duration_seconds = Histogram(
    'rag_rerank_duration_seconds',
    'RAG reranking latency in seconds',
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0)
)

# ==================== Database Metrics ====================

db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['operation', 'table', 'status']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query latency in seconds',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections'
)

db_connections_idle = Gauge(
    'db_connections_idle',
    'Number of idle database connections'
)

# ==================== Cache Metrics ====================

cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result']  # operation: get, set, delete; result: hit, miss, success, error
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate (0-1)'
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Cache size in bytes',
    ['cache_type']
)

# ==================== Agent Metrics ====================

agent_sessions_total = Counter(
    'agent_sessions_total',
    'Total agent sessions',
    ['status']  # active, completed, abandoned
)

agent_messages_total = Counter(
    'agent_messages_total',
    'Total agent messages',
    ['role', 'sales_state']
)

agent_state_transitions_total = Counter(
    'agent_state_transitions_total',
    'Total FSM state transitions',
    ['from_state', 'to_state', 'trigger']
)

agent_evaluation_score = Histogram(
    'agent_evaluation_score',
    'Agent evaluation scores',
    ['dimension'],  # overall, methodology, objection_handling, etc.
    buckets=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
)

# ==================== Voice Metrics ====================

voice_tts_requests_total = Counter(
    'voice_tts_requests_total',
    'Total TTS requests',
    ['emotion', 'status']
)

voice_tts_duration_seconds = Histogram(
    'voice_tts_duration_seconds',
    'TTS generation latency in seconds',
    ['emotion'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0)
)

voice_stt_requests_total = Counter(
    'voice_stt_requests_total',
    'Total STT requests',
    ['language', 'status']
)

voice_stt_duration_seconds = Histogram(
    'voice_stt_duration_seconds',
    'STT transcription latency in seconds',
    ['language'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

# ==================== Error Metrics ====================

errors_total = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'component']
)

# ==================== System Metrics ====================

system_info = Info(
    'system_info',
    'System information'
)

# ==================== Helper Functions ====================

def track_time(metric: Histogram, labels: dict = None):
    """
    Decorator to track execution time.

    Usage:
        @track_time(http_request_duration_seconds, {"method": "GET", "endpoint": "/api/v1/health"})
        async def handler():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def increment_counter(counter: Counter, labels: dict = None, value: float = 1):
    """Increment counter with labels."""
    if labels:
        counter.labels(**labels).inc(value)
    else:
        counter.inc(value)


def set_gauge(gauge: Gauge, value: float, labels: dict = None):
    """Set gauge value with labels."""
    if labels:
        gauge.labels(**labels).set(value)
    else:
        gauge.set(value)


def observe_histogram(histogram: Histogram, value: float, labels: dict = None):
    """Observe histogram value with labels."""
    if labels:
        histogram.labels(**labels).observe(value)
    else:
        histogram.observe(value)


# ==================== Metrics Collector ====================

class MetricsCollector:
    """
    Centralized metrics collector.

    Usage:
        collector = MetricsCollector()

        # Track HTTP request
        with collector.track_http_request("GET", "/api/v1/health"):
            # ... handle request ...
            collector.record_http_response(200)

        # Track LLM request
        with collector.track_llm_request("openai", "gpt-4o-mini"):
            # ... call LLM ...
            collector.record_llm_tokens("openai", "gpt-4o-mini", prompt_tokens=100, completion_tokens=50)
    """

    def __init__(self):
        self._http_start_time = None
        self._llm_start_time = None
        self._rag_start_time = None
        self._db_start_time = None

    def track_http_request(self, method: str, endpoint: str):
        """Context manager to track HTTP request."""
        class HTTPTracker:
            def __init__(self, collector, method, endpoint):
                self.collector = collector
                self.method = method
                self.endpoint = endpoint

            def __enter__(self):
                self.collector._http_start_time = time.time()
                active_connections.inc()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.collector._http_start_time
                http_request_duration_seconds.labels(
                    method=self.method,
                    endpoint=self.endpoint
                ).observe(duration)
                active_connections.dec()

        return HTTPTracker(self, method, endpoint)

    def record_http_response(self, method: str, endpoint: str, status: int):
        """Record HTTP response."""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()

    def track_llm_request(self, provider: str, model: str):
        """Context manager to track LLM request."""
        class LLMTracker:
            def __init__(self, collector, provider, model):
                self.collector = collector
                self.provider = provider
                self.model = model

            def __enter__(self):
                self.collector._llm_start_time = time.time()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.collector._llm_start_time
                status = "error" if exc_type else "success"

                llm_requests_total.labels(
                    provider=self.provider,
                    model=self.model,
                    status=status
                ).inc()

                llm_request_duration_seconds.labels(
                    provider=self.provider,
                    model=self.model
                ).observe(duration)

        return LLMTracker(self, provider, model)

    def record_llm_tokens(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int):
        """Record LLM token usage."""
        llm_tokens_total.labels(
            provider=provider,
            model=model,
            type="prompt"
        ).inc(prompt_tokens)

        llm_tokens_total.labels(
            provider=provider,
            model=model,
            type="completion"
        ).inc(completion_tokens)

    def track_rag_retrieval(self, search_mode: str):
        """Context manager to track RAG retrieval."""
        class RAGTracker:
            def __init__(self, collector, search_mode):
                self.collector = collector
                self.search_mode = search_mode

            def __enter__(self):
                self.collector._rag_start_time = time.time()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.collector._rag_start_time
                status = "error" if exc_type else "success"

                rag_retrieval_total.labels(
                    search_mode=self.search_mode,
                    status=status
                ).inc()

                rag_retrieval_duration_seconds.labels(
                    search_mode=self.search_mode
                ).observe(duration)

        return RAGTracker(self, search_mode)

    def record_rag_documents(self, count: int):
        """Record number of documents retrieved."""
        rag_documents_retrieved.observe(count)

    def track_db_query(self, operation: str, table: str):
        """Context manager to track database query."""
        class DBTracker:
            def __init__(self, collector, operation, table):
                self.collector = collector
                self.operation = operation
                self.table = table

            def __enter__(self):
                self.collector._db_start_time = time.time()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.collector._db_start_time
                status = "error" if exc_type else "success"

                db_queries_total.labels(
                    operation=self.operation,
                    table=self.table,
                    status=status
                ).inc()

                db_query_duration_seconds.labels(
                    operation=self.operation,
                    table=self.table
                ).observe(duration)

        return DBTracker(self, operation, table)

    def record_cache_operation(self, operation: str, result: str):
        """Record cache operation."""
        cache_operations_total.labels(
            operation=operation,
            result=result
        ).inc()

    def update_cache_hit_rate(self, hit_rate: float):
        """Update cache hit rate."""
        cache_hit_rate.set(hit_rate)

    def record_agent_session(self, status: str):
        """Record agent session."""
        agent_sessions_total.labels(status=status).inc()

    def record_agent_message(self, role: str, sales_state: str):
        """Record agent message."""
        agent_messages_total.labels(
            role=role,
            sales_state=sales_state
        ).inc()

    def record_state_transition(self, from_state: str, to_state: str, trigger: str):
        """Record FSM state transition."""
        agent_state_transitions_total.labels(
            from_state=from_state,
            to_state=to_state,
            trigger=trigger
        ).inc()

    def record_evaluation_score(self, dimension: str, score: float):
        """Record evaluation score."""
        agent_evaluation_score.labels(dimension=dimension).observe(score)

    def record_error(self, error_type: str, component: str):
        """Record error."""
        errors_total.labels(
            error_type=error_type,
            component=component
        ).inc()


# Global collector instance
collector = MetricsCollector()


# ==================== Initialization ====================

def init_metrics():
    """Initialize metrics with system information."""
    import platform
    import sys

    system_info.info({
        'python_version': sys.version,
        'platform': platform.platform(),
        'processor': platform.processor(),
    })

    logger.info("Metrics initialized")


# Initialize on import
init_metrics()
