"""Prometheus metrics for production monitoring."""
from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, Info

# ── HTTP Request Metrics ──────────────────────────────────────────────────

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_request_errors_total = Counter(
    "http_request_errors_total",
    "Total HTTP request errors",
    ["method", "endpoint", "error_type"],
)

# ── Session Metrics ───────────────────────────────────────────────────────

active_sessions = Gauge(
    "active_sessions",
    "Number of active chat sessions",
)

session_messages_total = Counter(
    "session_messages_total",
    "Total messages processed",
    ["role"],
)

# ── LLM Gateway Metrics ───────────────────────────────────────────────────

llm_api_calls_total = Counter(
    "llm_api_calls_total",
    "Total LLM API calls",
    ["provider", "model", "task"],
)

llm_api_duration_seconds = Histogram(
    "llm_api_duration_seconds",
    "LLM API call duration",
    ["provider", "model", "task"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

llm_api_errors_total = Counter(
    "llm_api_errors_total",
    "Total LLM API errors",
    ["provider", "model", "error_type"],
)

llm_api_tokens_total = Counter(
    "llm_api_tokens_total",
    "Total tokens consumed",
    ["provider", "model", "token_type"],
)

# ── Circuit Breaker Metrics ───────────────────────────────────────────────

circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["name"],
)

circuit_breaker_failures_total = Counter(
    "circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["name"],
)

circuit_breaker_successes_total = Counter(
    "circuit_breaker_successes_total",
    "Total circuit breaker successes",
    ["name"],
)

# ── Database Metrics ──────────────────────────────────────────────────────

db_connections_active = Gauge(
    "db_connections_active",
    "Active database connections",
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

db_errors_total = Counter(
    "db_errors_total",
    "Total database errors",
    ["error_type"],
)

# ── Redis Cache Metrics ───────────────────────────────────────────────────

redis_operations_total = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],
)

redis_cache_hits_total = Counter(
    "redis_cache_hits_total",
    "Total cache hits",
)

redis_cache_misses_total = Counter(
    "redis_cache_misses_total",
    "Total cache misses",
)

redis_fallback_active = Gauge(
    "redis_fallback_active",
    "Whether Redis fallback (in-memory) is active (1=yes, 0=no)",
)

# ── Guard Metrics ─────────────────────────────────────────────────────────

guard_checks_total = Counter(
    "guard_checks_total",
    "Total guard checks",
    ["risk_type", "severity"],
)

guard_rewrites_total = Counter(
    "guard_rewrites_total",
    "Total guard rewrites",
)

# ── FSM Metrics ───────────────────────────────────────────────────────────

fsm_transitions_total = Counter(
    "fsm_transitions_total",
    "Total FSM state transitions",
    ["from_stage", "to_stage", "signal"],
)

fsm_current_stage = Gauge(
    "fsm_current_stage",
    "Current FSM stage distribution",
    ["stage"],
)

# ── System Info ───────────────────────────────────────────────────────────

system_info = Info(
    "salesagent_system",
    "SalesAgent system information",
)
