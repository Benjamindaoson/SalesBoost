"""
Production Readiness Checklist and Day 2 Operations Guide
==========================================================

Based on architect review, this document outlines critical production requirements
and operational procedures for the Coordinator Improvements system.

CRITICAL FIXES REQUIRED
=======================

1. CELERY WORKER - MANDATORY (NOT OPTIONAL!)
   Status: CRITICAL - Must be running for async coach functionality

   Issue:
   - Report incorrectly listed Celery as "optional"
   - Without worker, tasks accumulate in Redis queue
   - Users will never receive coach suggestions

   Fix:
   ```bash
   # Start Celery Worker (Production)
   celery -A app.tasks.coach_tasks worker --loglevel=info --pool=solo

   # Or use the startup script
   start_celery_worker.bat
   ```

   Verification:
   ```bash
   # Check worker status
   celery -A app.tasks.coach_tasks inspect active

   # Check queue length
   redis-cli llen celery
   ```

2. SYSTEM STATUS CORRECTION
   Current: "degraded (expected)"
   Should be: "healthy" when all required services are running

   Required Services:
   - Redis (Port 6379) ✓
   - FastAPI (Port 8000) ✓
   - Celery Worker ✗ (MUST START)

DAY 2 OPERATIONS ROADMAP
========================

Phase 1: Observability (Week 1)
--------------------------------

1.1 Grafana Dashboard Setup
   Priority: HIGH

   Panels to Create:

   a) Bandit Performance Dashboard
      - Exploration vs Exploitation ratio
      - UCB scores distribution
      - Arm selection frequency
      - Average reward per arm

      Queries:
      ```promql
      # Exploration rate
      rate(coordinator_bandit_decisions_total{exploration="true"}[5m]) /
      rate(coordinator_bandit_decisions_total[5m])

      # Average reward by arm
      rate(coordinator_user_feedback_total[5m]) by (arm)
      ```

   b) Coordinator Health Dashboard
      - Node execution latency (p50, p95, p99)
      - Routing decision confidence
      - Error rate by node type
      - Active sessions

      Queries:
      ```promql
      # P95 latency
      histogram_quantile(0.95,
        rate(coordinator_node_execution_duration_seconds_bucket[5m]))

      # Error rate
      rate(coordinator_node_execution_total{status="error"}[5m])
      ```

   c) Celery Queue Dashboard
      - Queue length
      - Task processing rate
      - Task failure rate
      - Worker utilization

      Queries:
      ```promql
      # Queue backlog
      celery_queue_length{queue="default"}

      # Processing rate
      rate(celery_tasks_total{state="SUCCESS"}[5m])
      ```

1.2 Alerting Rules

   Critical Alerts:
   ```yaml
   # Celery worker down
   - alert: CeleryWorkerDown
     expr: up{job="celery"} == 0
     for: 1m
     severity: critical

   # Queue backlog
   - alert: CeleryQueueBacklog
     expr: celery_queue_length > 100
     for: 5m
     severity: warning

   # High error rate
   - alert: CoordinatorHighErrorRate
     expr: rate(coordinator_node_execution_total{status="error"}[5m]) > 0.1
     for: 5m
     severity: warning
   ```

Phase 2: Bandit Cold Start Strategy (Week 1-2)
-----------------------------------------------

2.1 Initial Exploration Phase
   Problem: LinUCB needs data to learn optimal policy

   Solution: Implement warm-up period

   ```python
   # In bandit_linucb.py
   class LinUCBBandit:
       def __init__(self, arms, context_dim, alpha=0.5, warmup_pulls=1000):
           self.warmup_pulls = warmup_pulls
           self.total_pulls = 0

       def choose(self, context):
           # Force exploration during warmup
           if self.total_pulls < self.warmup_pulls:
               # Uniform random selection
               return random.choice(self.arms)

           # Normal LinUCB after warmup
           return self._linucb_select(context)
   ```

2.2 Default Arm Weights
   Give initial bias to known-good strategies:

   ```python
   # Initialize with prior knowledge
   default_rewards = {
       "npc": 0.7,      # NPC responses generally good
       "tools": 0.6,    # Tools useful but slower
       "knowledge": 0.5 # Knowledge base hit-or-miss
   }

   for arm, reward in default_rewards.items():
       for _ in range(10):  # Simulate 10 successful pulls
           bandit.record_feedback(arm, reward)
   ```

2.3 Monitoring Cold Start
   Track when bandit transitions from exploration to exploitation:

   ```python
   # Add metric
   coordinator_metrics.record_bandit_phase(
       phase="warmup" if pulls < warmup_pulls else "learned"
   )
   ```

Phase 3: Load Testing (Week 2)
-------------------------------

3.1 Test Scenarios

   a) Baseline Load Test
      - 100 concurrent users
      - 1000 requests over 5 minutes
      - Measure: p95 latency, error rate

   b) Spike Test
      - Sudden burst: 0 → 500 users in 10 seconds
      - Measure: queue backlog, recovery time

   c) Soak Test
      - 50 concurrent users
      - 24 hours continuous
      - Measure: memory leaks, connection pool exhaustion

3.2 Locust Test Script

   ```python
   # locustfile.py
   from locust import HttpUser, task, between

   class CoordinatorUser(HttpUser):
       wait_time = between(1, 3)

       @task(3)
       def chat_message(self):
           self.client.post("/ws/chat", json={
               "session_id": f"load_test_{self.user_id}",
               "message": "What's the price?",
               "user_id": self.user_id
           })

       @task(1)
       def submit_feedback(self):
           self.client.post("/api/v1/feedback/submit", json={
               "session_id": f"load_test_{self.user_id}",
               "turn_number": 1,
               "rating": 5
           })
   ```

   Run:
   ```bash
   locust -f locustfile.py --host=http://localhost:8000
   ```

3.3 Bottleneck Analysis

   Expected Bottlenecks:
   1. Redis connection pool (default: 50 connections)
      Fix: Increase pool size in core/redis.py

   2. DAG validation overhead
      Fix: Cache validated workflows in Redis

   3. LLM API rate limits
      Fix: Implement request queuing and backoff

Phase 4: Production Hardening (Week 3)
---------------------------------------

4.1 Service Management

   Use Supervisor (Linux) or NSSM (Windows):

   ```ini
   # supervisor.conf
   [program:celery_worker]
   command=celery -A app.tasks.coach_tasks worker --loglevel=info
   directory=/opt/salesboost
   user=salesboost
   autostart=true
   autorestart=true
   redirect_stderr=true
   stdout_logfile=/var/log/celery/worker.log
   ```

4.2 Health Checks

   Add liveness and readiness probes:

   ```python
   # In main.py
   @app.get("/health/live")
   async def liveness():
       return {"status": "alive"}

   @app.get("/health/ready")
   async def readiness():
       checks = {
           "redis": await check_redis(),
           "celery": await check_celery_worker(),
           "db": await check_database()
       }

       if all(checks.values()):
           return {"status": "ready", "checks": checks}
       else:
           raise HTTPException(503, detail=checks)
   ```

4.3 Graceful Shutdown

   Ensure tasks complete before shutdown:

   ```python
   # In lifespan
   async def shutdown():
       # Stop accepting new tasks
       await celery_app.control.cancel_consumer('default')

       # Wait for active tasks (max 30s)
       for _ in range(30):
           active = celery_app.control.inspect().active()
           if not active or not any(active.values()):
               break
           await asyncio.sleep(1)

       # Force shutdown
       await celery_app.control.shutdown()
   ```

IMMEDIATE ACTION ITEMS
======================

Priority 1 (Today):
[ ] Start Celery Worker
[ ] Verify worker is processing tasks
[ ] Update health check to require Celery

Priority 2 (This Week):
[ ] Set up Grafana dashboards
[ ] Configure alerting rules
[ ] Implement Bandit warm-up period
[ ] Add default arm weights

Priority 3 (Next Week):
[ ] Run load tests with Locust
[ ] Analyze bottlenecks
[ ] Implement caching for DAG validation
[ ] Set up Supervisor/NSSM for service management

Priority 4 (Week 3):
[ ] Add liveness/readiness probes
[ ] Implement graceful shutdown
[ ] Document runbook procedures
[ ] Train operations team

MONITORING CHECKLIST
====================

Daily:
- [ ] Check Celery queue length
- [ ] Review error logs
- [ ] Verify all workers are active

Weekly:
- [ ] Review Bandit performance metrics
- [ ] Analyze user feedback trends
- [ ] Check for memory leaks
- [ ] Review slow query logs

Monthly:
- [ ] Capacity planning review
- [ ] Update Bandit parameters based on data
- [ ] Review and update alerting thresholds
- [ ] Disaster recovery drill

CONCLUSION
==========

The coordinator improvements are code-complete, but production readiness requires:

1. CRITICAL: Start Celery Worker (not optional!)
2. Set up comprehensive monitoring
3. Implement cold start strategy for Bandit
4. Conduct load testing
5. Harden service management

Estimated time to full production readiness: 2-3 weeks

Remember: "养育" (nurturing) AI systems is an ongoing process. The real work
begins after deployment!
