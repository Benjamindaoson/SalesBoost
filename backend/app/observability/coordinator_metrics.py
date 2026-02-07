"""
Coordinator Metrics for Prometheus
Provides detailed metrics for workflow orchestration monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Optional

# ==================== Node Execution Metrics ====================

node_execution_total = Counter(
    'coordinator_node_execution_total',
    'Total number of node executions',
    ['node_type', 'status', 'engine']
)

node_execution_duration_seconds = Histogram(
    'coordinator_node_execution_duration_seconds',
    'Node execution duration in seconds',
    ['node_type', 'engine'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# ==================== Routing Metrics ====================

routing_decision_total = Counter(
    'coordinator_routing_decision_total',
    'Total number of routing decisions',
    ['source', 'target_node', 'engine']
)

routing_confidence = Histogram(
    'coordinator_routing_confidence',
    'Routing decision confidence scores',
    ['source', 'engine'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# ==================== Reasoning Engine Metrics ====================

reasoning_execution_total = Counter(
    'coordinator_reasoning_execution_total',
    'Total number of reasoning engine executions',
    ['status', 'source']
)

reasoning_duration_seconds = Histogram(
    'coordinator_reasoning_duration_seconds',
    'Reasoning engine execution duration',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

# ==================== Bandit Metrics ====================

bandit_decision_total = Counter(
    'coordinator_bandit_decision_total',
    'Total number of bandit decisions',
    ['chosen_arm', 'exploration']
)

bandit_reward_total = Counter(
    'coordinator_bandit_reward_total',
    'Total rewards received by bandit',
    ['arm']
)

bandit_arm_score = Gauge(
    'coordinator_bandit_arm_score',
    'Current score for each bandit arm',
    ['arm']
)

bandit_arm_pulls = Gauge(
    'coordinator_bandit_arm_pulls',
    'Total pulls for each bandit arm',
    ['arm']
)

# ==================== Coach Advice Metrics ====================

coach_advice_total = Counter(
    'coordinator_coach_advice_total',
    'Total coach advice generations',
    ['source', 'intent']
)

coach_fallback_total = Counter(
    'coordinator_coach_fallback_total',
    'Total coach fallback activations',
    ['intent', 'reason']
)

# ==================== Compliance Metrics ====================

compliance_check_total = Counter(
    'coordinator_compliance_check_total',
    'Total compliance checks',
    ['risk_level', 'requires_review']
)

compliance_risk_score = Histogram(
    'coordinator_compliance_risk_score',
    'Compliance risk scores',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# ==================== Turn Execution Metrics ====================

turn_execution_total = Counter(
    'coordinator_turn_execution_total',
    'Total turn executions',
    ['engine', 'status']
)

turn_ttft_seconds = Histogram(
    'coordinator_turn_ttft_seconds',
    'Time to first token (TTFT) in seconds',
    ['engine', 'async_coach'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
)

turn_total_duration_seconds = Histogram(
    'coordinator_turn_total_duration_seconds',
    'Total turn execution duration',
    ['engine'],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 30.0]
)

# ==================== User Feedback Metrics ====================

user_feedback_total = Counter(
    'coordinator_user_feedback_total',
    'Total user feedback submissions',
    ['rating', 'intent']
)

user_satisfaction_score = Histogram(
    'coordinator_user_satisfaction_score',
    'User satisfaction scores (1-5)',
    buckets=[1.0, 2.0, 3.0, 4.0, 5.0]
)

# ==================== Configuration Metrics ====================

workflow_config_info = Info(
    'coordinator_workflow_config',
    'Current workflow configuration'
)

active_nodes = Gauge(
    'coordinator_active_nodes',
    'Number of active nodes in workflow',
    ['engine']
)

# ==================== Helper Functions ====================

def record_node_execution(
    node_type: str,
    duration_seconds: float,
    status: str = "ok",
    engine: str = "dynamic_workflow"
):
    """Record node execution metrics"""
    node_execution_total.labels(
        node_type=node_type,
        status=status,
        engine=engine
    ).inc()

    node_execution_duration_seconds.labels(
        node_type=node_type,
        engine=engine
    ).observe(duration_seconds)


def record_routing_decision(
    source: str,
    target_node: str,
    confidence: float,
    engine: str = "dynamic_workflow"
):
    """Record routing decision metrics"""
    routing_decision_total.labels(
        source=source,
        target_node=target_node,
        engine=engine
    ).inc()

    routing_confidence.labels(
        source=source,
        engine=engine
    ).observe(confidence)


def record_reasoning_execution(
    duration_seconds: float,
    status: str = "ok",
    source: str = "llm"
):
    """Record reasoning engine metrics"""
    reasoning_execution_total.labels(
        status=status,
        source=source
    ).inc()

    reasoning_duration_seconds.observe(duration_seconds)


def record_bandit_decision(
    chosen_arm: str,
    exploration: bool,
    score: float
):
    """Record bandit decision metrics"""
    bandit_decision_total.labels(
        chosen_arm=chosen_arm,
        exploration=str(exploration)
    ).inc()

    bandit_arm_score.labels(arm=chosen_arm).set(score)


def record_bandit_feedback(
    arm: str,
    reward: float,
    total_pulls: int
):
    """Record bandit feedback metrics"""
    bandit_reward_total.labels(arm=arm).inc(reward)
    bandit_arm_pulls.labels(arm=arm).set(total_pulls)


def record_coach_advice(
    source: str,
    intent: str,
    is_fallback: bool = False,
    fallback_reason: Optional[str] = None
):
    """Record coach advice metrics"""
    coach_advice_total.labels(
        source=source,
        intent=intent
    ).inc()

    if is_fallback and fallback_reason:
        coach_fallback_total.labels(
            intent=intent,
            reason=fallback_reason
        ).inc()


def record_compliance_check(
    risk_level: str,
    risk_score: float,
    requires_review: bool
):
    """Record compliance check metrics"""
    compliance_check_total.labels(
        risk_level=risk_level,
        requires_review=str(requires_review)
    ).inc()

    compliance_risk_score.observe(risk_score)


def record_turn_execution(
    engine: str,
    ttft_seconds: float,
    total_duration_seconds: float,
    status: str = "ok",
    async_coach: bool = False
):
    """Record turn execution metrics"""
    turn_execution_total.labels(
        engine=engine,
        status=status
    ).inc()

    turn_ttft_seconds.labels(
        engine=engine,
        async_coach=str(async_coach)
    ).observe(ttft_seconds)

    turn_total_duration_seconds.labels(
        engine=engine
    ).observe(total_duration_seconds)


def record_user_feedback(
    rating: int,
    intent: str
):
    """Record user feedback metrics"""
    user_feedback_total.labels(
        rating=str(rating),
        intent=intent
    ).inc()

    user_satisfaction_score.observe(float(rating))


def update_workflow_config(
    engine: str,
    enabled_nodes: int,
    config_name: str,
    version: str
):
    """Update workflow configuration info"""
    workflow_config_info.info({
        'engine': engine,
        'config_name': config_name,
        'version': version
    })

    active_nodes.labels(engine=engine).set(enabled_nodes)
