# 🔧 SalesBoost RAG 3.0 - Operations Manual & Troubleshooting Guide

**Version:** 3.0
**Date:** 2026-02-02
**Status:** ✅ Production Ready

---

## 📋 Table of Contents

1. [Operations Manual](#operations-manual)
2. [Deployment Guide](#deployment-guide)
3. [Monitoring & Alerting](#monitoring--alerting)
4. [Troubleshooting Guide](#troubleshooting-guide)
5. [Performance Tuning](#performance-tuning)
6. [Disaster Recovery](#disaster-recovery)

---

## Operations Manual

### Daily Operations

#### 1. Health Check

**Morning Checklist:**
```bash
# Check service status
curl http://localhost:8000/health

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Grafana dashboards
open http://localhost:3000

# Check error logs
docker logs salesboost-rag --tail 100 | grep ERROR
```

**Expected Results:**
- Health endpoint returns 200 OK
- All Prometheus targets are UP
- Grafana shows green metrics
- No critical errors in logs

#### 2. Performance Monitoring

**Key Metrics to Watch:**
```bash
# Query rate (should be stable)
curl 'http://localhost:9090/api/v1/query?query=rate(production_rag_query_total[5m])'

# P99 latency (should be < 500ms)
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.99,rate(production_rag_latency_seconds_bucket[5m]))'

# Error rate (should be < 1%)
curl 'http://localhost:9090/api/v1/query?query=rate(production_rag_errors_total[5m])'

# Cache hit rate (should be > 30%)
curl 'http://localhost:9090/api/v1/query?query=production_rag_cache_hit_rate'
```

#### 3. Cost Monitoring

**Daily Cost Check:**
```bash
# Check daily cost
curl 'http://localhost:9090/api/v1/query?query=increase(production_rag_cost_cny[24h])'

# Check cost by service
curl 'http://localhost:9090/api/v1/query?query=increase(production_rag_cost_cny[24h])' | jq '.data.result[] | {service: .metric.service, cost: .value[1]}'
```

**Cost Alerts:**
- Daily cost > ¥100: Warning
- Daily cost > ¥200: Critical
- Hourly cost > ¥10: Warning

### Weekly Operations

#### 1. Performance Review

**Weekly Report:**
```bash
# Generate weekly report
python scripts/generate_weekly_report.py --start-date 2026-01-26 --end-date 2026-02-02

# Key metrics:
# - Average QPS
# - P99 latency trend
# - Error rate trend
# - Cost trend
# - Cache hit rate trend
```

#### 2. Capacity Planning

**Resource Usage Check:**
```bash
# Check CPU usage
docker stats salesboost-rag --no-stream

# Check memory usage
docker stats salesboost-rag --no-stream | awk '{print $4}'

# Check disk usage
df -h | grep /var/lib/docker

# Check Qdrant storage
du -sh /var/lib/qdrant
```

**Scaling Triggers:**
- CPU > 70% for 1 hour → Scale up
- Memory > 80% for 1 hour → Scale up
- Disk > 80% → Add storage
- QPS > 1000 sustained → Add instances

#### 3. Backup Verification

**Backup Check:**
```bash
# Check latest backup
ls -lh /backups/qdrant/ | tail -5

# Verify backup integrity
python scripts/verify_backup.py --backup-path /backups/qdrant/latest

# Test restore (on staging)
python scripts/restore_backup.py --backup-path /backups/qdrant/latest --target staging
```

### Monthly Operations

#### 1. Security Audit

**Security Checklist:**
- [ ] Review access logs
- [ ] Check for suspicious activity
- [ ] Update dependencies
- [ ] Rotate API keys
- [ ] Review firewall rules

#### 2. Performance Optimization

**Optimization Review:**
- [ ] Analyze slow queries
- [ ] Review cache hit rates
- [ ] Optimize vector indices
- [ ] Update model versions
- [ ] Fine-tune configurations

#### 3. Documentation Update

**Documentation Tasks:**
- [ ] Update runbooks
- [ ] Document new issues
- [ ] Update architecture diagrams
- [ ] Review alert thresholds
- [ ] Update cost estimates

---

## Deployment Guide

### Initial Deployment

#### 1. Prerequisites

**System Requirements:**
- Docker 20.10+
- Docker Compose 2.0+
- 16GB RAM minimum
- 100GB disk space
- Ubuntu 20.04+ or similar

**Environment Setup:**
```bash
# Clone repository
git clone https://github.com/your-org/salesboost.git
cd salesboost

# Create environment file
cp .env.example .env

# Edit configuration
nano .env
```

#### 2. Deploy Services

**Start Core Services:**
```bash
# Start Qdrant
docker-compose up -d qdrant

# Wait for Qdrant to be ready
until curl -f http://localhost:6333/health; do sleep 1; done

# Start Redis
docker-compose up -d redis

# Start PostgreSQL
docker-compose up -d postgres

# Start RAG application
docker-compose up -d rag-app

# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d
```

**Verify Deployment:**
```bash
# Check all services are running
docker-compose ps

# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:6333/health
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
```

#### 3. Initialize Data

**Load Initial Data:**
```bash
# Create Qdrant collection
python scripts/create_collection.py

# Load embeddings
python scripts/load_embeddings.py --data-path ./data/knowledge_base

# Verify data loaded
curl http://localhost:6333/collections/sales_knowledge
```

### Rolling Update

**Zero-Downtime Update:**
```bash
# Pull latest image
docker pull your-registry/salesboost-rag:latest

# Update one instance at a time
for i in 1 2 3; do
    docker-compose stop rag-app-$i
    docker-compose up -d rag-app-$i
    sleep 30  # Wait for health check
    curl http://localhost:800$i/health || exit 1
done
```

### Rollback Procedure

**Emergency Rollback:**
```bash
# Rollback to previous version
docker-compose down
docker-compose up -d --force-recreate --build

# Or rollback to specific version
docker pull your-registry/salesboost-rag:v2.9
docker-compose up -d
```

---

## Monitoring & Alerting

### Prometheus Queries

**Useful Queries:**

1. **Query Rate:**
```promql
rate(production_rag_query_total[5m])
```

2. **P99 Latency:**
```promql
histogram_quantile(0.99, rate(production_rag_latency_seconds_bucket{stage="total"}[5m]))
```

3. **Error Rate:**
```promql
rate(production_rag_errors_total[5m]) / rate(production_rag_query_total[5m])
```

4. **Cache Hit Rate:**
```promql
production_rag_cache_hit_rate{cache_type="semantic"}
```

5. **Cost per Hour:**
```promql
rate(production_rag_cost_cny[1h]) * 3600
```

### Alert Configuration

**Critical Alerts (PagerDuty):**
- ServiceDown
- HighErrorRate (> 5%)
- P99Latency > 1000ms

**Warning Alerts (Slack):**
- HighP99Latency (> 500ms)
- LowCacheHitRate (< 30%)
- HighCost (> ¥10/hour)
- HighConcurrency (> 800)

### Grafana Dashboards

**Main Dashboard Panels:**
1. Query Rate (QPS)
2. Latency Distribution (P50/P95/P99)
3. Error Rate
4. Cache Hit Rate
5. Cost Tracking
6. Concurrent Queries
7. Success Rate
8. Query Complexity Distribution

---

## Troubleshooting Guide

### Common Issues

#### Issue 1: High Latency

**Symptoms:**
- P99 latency > 500ms
- Users complaining about slow responses
- Grafana shows red latency metrics

**Diagnosis:**
```bash
# Check which stage is slow
curl 'http://localhost:9090/api/v1/query?query=rate(production_rag_latency_seconds_sum[5m])/rate(production_rag_latency_seconds_count[5m])' | jq '.data.result[] | {stage: .metric.stage, latency: .value[1]}'

# Check concurrent queries
curl 'http://localhost:9090/api/v1/query?query=production_rag_concurrent_queries'

# Check resource usage
docker stats salesboost-rag
```

**Solutions:**

1. **If retrieval is slow:**
```bash
# Check Qdrant health
curl http://localhost:6333/health

# Check Qdrant collection size
curl http://localhost:6333/collections/sales_knowledge

# Restart Qdrant if needed
docker-compose restart qdrant
```

2. **If generation is slow:**
```bash
# Check LLM API status
curl https://api.siliconflow.cn/v1/models

# Switch to faster model
# Edit .env: SILICONFLOW_MODEL=deepseek-7b
docker-compose restart rag-app
```

3. **If cache is not helping:**
```bash
# Check cache hit rate
curl 'http://localhost:9090/api/v1/query?query=production_rag_cache_hit_rate'

# Clear and rebuild cache
redis-cli FLUSHDB
docker-compose restart rag-app
```

#### Issue 2: High Error Rate

**Symptoms:**
- Error rate > 1%
- Errors in logs
- Failed requests

**Diagnosis:**
```bash
# Check error types
curl 'http://localhost:9090/api/v1/query?query=rate(production_rag_errors_total[5m])' | jq '.data.result[] | {error_type: .metric.error_type, rate: .value[1]}'

# Check recent errors
docker logs salesboost-rag --tail 100 | grep ERROR

# Check circuit breaker state
curl http://localhost:8000/metrics | grep circuit_breaker_state
```

**Solutions:**

1. **If LLM API errors:**
```bash
# Check API key
echo $SILICONFLOW_API_KEY

# Test API directly
curl -H "Authorization: Bearer $SILICONFLOW_API_KEY" \
     https://api.siliconflow.cn/v1/models

# Rotate API key if needed
# Update .env and restart
```

2. **If Qdrant errors:**
```bash
# Check Qdrant logs
docker logs qdrant --tail 100

# Check collection health
curl http://localhost:6333/collections/sales_knowledge

# Recreate collection if corrupted
python scripts/recreate_collection.py
```

3. **If timeout errors:**
```bash
# Increase timeouts in .env
QUERY_TIMEOUT_SECONDS=10
RETRIEVAL_TIMEOUT_MS=200
GENERATION_TIMEOUT_MS=2000

# Restart application
docker-compose restart rag-app
```

#### Issue 3: High Cost

**Symptoms:**
- Daily cost > ¥100
- Cost alert triggered
- Budget exceeded

**Diagnosis:**
```bash
# Check cost by service
curl 'http://localhost:9090/api/v1/query?query=increase(production_rag_cost_cny[24h])' | jq '.data.result[] | {service: .metric.service, cost: .value[1]}'

# Check query distribution
curl 'http://localhost:9090/api/v1/query?query=sum by (complexity) (rate(production_rag_query_total[1h]))'

# Check model usage
grep "model=" /var/log/salesboost/rag.log | tail -100
```

**Solutions:**

1. **Enable cost-aware routing:**
```bash
# Edit .env
ENABLE_COST_AWARE_ROUTING=true
DAILY_BUDGET_CNY=100

# Restart application
docker-compose restart rag-app
```

2. **Use cheaper models:**
```bash
# Edit .env
SILICONFLOW_MODEL=deepseek-7b  # Instead of deepseek-v3

# Restart application
docker-compose restart rag-app
```

3. **Increase cache hit rate:**
```bash
# Lower semantic cache threshold
SEMANTIC_CACHE_THRESHOLD=0.90  # From 0.95

# Increase cache size
L1_CACHE_SIZE=500  # From 100

# Restart application
docker-compose restart rag-app
```

#### Issue 4: Low Cache Hit Rate

**Symptoms:**
- Cache hit rate < 30%
- High latency
- High cost

**Diagnosis:**
```bash
# Check cache statistics
curl http://localhost:8000/metrics | grep cache_hit_rate

# Check cache size
redis-cli INFO memory

# Check query diversity
curl 'http://localhost:9090/api/v1/query?query=count(production_rag_query_total)'
```

**Solutions:**

1. **Lower cache threshold:**
```bash
# Edit .env
SEMANTIC_CACHE_THRESHOLD=0.90  # From 0.95

# Restart application
docker-compose restart rag-app
```

2. **Increase cache size:**
```bash
# Edit .env
L1_CACHE_SIZE=500
L2_CACHE_SIZE=5000

# Restart application
docker-compose restart rag-app
```

3. **Enable cache warmup:**
```bash
# Run cache warmup script
python scripts/warmup_cache.py --queries 1000

# Verify cache hit rate improved
curl http://localhost:8000/metrics | grep cache_hit_rate
```

#### Issue 5: Service Down

**Symptoms:**
- Health check fails
- Service unreachable
- Critical alert triggered

**Diagnosis:**
```bash
# Check if container is running
docker ps | grep salesboost-rag

# Check container logs
docker logs salesboost-rag --tail 100

# Check resource usage
docker stats salesboost-rag --no-stream

# Check port binding
netstat -tulpn | grep 8000
```

**Solutions:**

1. **Restart service:**
```bash
# Restart container
docker-compose restart rag-app

# Wait for health check
until curl -f http://localhost:8000/health; do sleep 1; done
```

2. **Check dependencies:**
```bash
# Check Qdrant
curl http://localhost:6333/health

# Check Redis
redis-cli PING

# Check PostgreSQL
docker-compose exec postgres pg_isready
```

3. **Emergency recovery:**
```bash
# Stop all services
docker-compose down

# Clean up
docker system prune -f

# Restart all services
docker-compose up -d

# Verify health
curl http://localhost:8000/health
```

---

## Performance Tuning

### Latency Optimization

**Configuration Profiles:**

1. **Latency-Optimized:**
```bash
# .env configuration
SIMPLE_QUERY_DIMENSION=64
SIMPLE_QUERY_CANDIDATES=10
SEMANTIC_CACHE_THRESHOLD=0.98
ENABLE_BATCHING=false
ENABLE_PREFETCH=true
```

2. **Throughput-Optimized:**
```bash
# .env configuration
MAX_CONCURRENT_QUERIES=2000
ENABLE_BATCHING=true
BATCH_SIZE=64
QDRANT_CONNECTION_POOL_SIZE=200
```

3. **Cost-Optimized:**
```bash
# .env configuration
SIMPLE_QUERY_DIMENSION=64
MEDIUM_QUERY_DIMENSION=128
COMPLEX_QUERY_DIMENSION=512
SEMANTIC_CACHE_THRESHOLD=0.90
CACHE_TTL_SECONDS=7200
```

### Resource Optimization

**Memory Optimization:**
```bash
# Reduce cache sizes
L1_CACHE_SIZE=50
L2_CACHE_SIZE=500

# Enable compression
ENABLE_COMPRESSION=true

# Restart application
docker-compose restart rag-app
```

**CPU Optimization:**
```bash
# Reduce concurrency
MAX_CONCURRENT_QUERIES=500
MAX_CONCURRENT_RETRIEVALS=50

# Disable expensive features
ENABLE_MULTI_QUERY=false

# Restart application
docker-compose restart rag-app
```

---

## Disaster Recovery

### Backup Procedures

**Daily Backup:**
```bash
# Backup Qdrant data
docker exec qdrant qdrant-backup create --collection sales_knowledge --output /backups/qdrant/$(date +%Y%m%d).snapshot

# Backup PostgreSQL
docker exec postgres pg_dump -U postgres salesboost > /backups/postgres/$(date +%Y%m%d).sql

# Backup Redis (if needed)
docker exec redis redis-cli SAVE
cp /var/lib/redis/dump.rdb /backups/redis/$(date +%Y%m%d).rdb
```

**Backup Verification:**
```bash
# Verify backup exists
ls -lh /backups/qdrant/$(date +%Y%m%d).snapshot
ls -lh /backups/postgres/$(date +%Y%m%d).sql

# Test restore on staging
python scripts/test_restore.py --backup-date $(date +%Y%m%d)
```

### Restore Procedures

**Full Restore:**
```bash
# Stop services
docker-compose down

# Restore Qdrant
docker exec qdrant qdrant-backup restore --collection sales_knowledge --input /backups/qdrant/20260201.snapshot

# Restore PostgreSQL
docker exec -i postgres psql -U postgres salesboost < /backups/postgres/20260201.sql

# Restore Redis
cp /backups/redis/20260201.rdb /var/lib/redis/dump.rdb

# Start services
docker-compose up -d

# Verify restore
curl http://localhost:8000/health
python scripts/verify_data.py
```

### Failover Procedures

**Primary Failure:**
```bash
# Promote replica to primary
docker exec postgres pg_ctl promote

# Update application configuration
# Edit .env: DATABASE_URL=postgresql://replica:5432/salesboost

# Restart application
docker-compose restart rag-app

# Verify failover
curl http://localhost:8000/health
```

---

## Appendix

### Useful Commands

**Docker:**
```bash
# View logs
docker logs salesboost-rag -f

# Execute command in container
docker exec -it salesboost-rag bash

# Check resource usage
docker stats

# Clean up
docker system prune -a
```

**Prometheus:**
```bash
# Query metrics
curl 'http://localhost:9090/api/v1/query?query=up'

# Check targets
curl 'http://localhost:9090/api/v1/targets'

# Reload configuration
curl -X POST http://localhost:9090/-/reload
```

**Grafana:**
```bash
# Export dashboard
curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
     http://localhost:3000/api/dashboards/uid/salesboost-rag > dashboard.json

# Import dashboard
curl -X POST -H "Content-Type: application/json" \
     -H "Authorization: Bearer $GRAFANA_API_KEY" \
     -d @dashboard.json \
     http://localhost:3000/api/dashboards/db
```

### Contact Information

**On-Call Rotation:**
- Primary: ops-team@salesboost.com
- Secondary: dev-team@salesboost.com
- Escalation: cto@salesboost.com

**Support Channels:**
- Slack: #salesboost-ops
- PagerDuty: salesboost-rag
- Email: ops@salesboost.com

---

**Document Version:** 3.0
**Last Updated:** 2026-02-02
**Maintainer:** Operations Team
