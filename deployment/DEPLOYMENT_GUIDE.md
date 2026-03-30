# Deployment Guide for Growth Flywheel 2.5

This guide covers deployment configurations for the SalesBoost Growth Flywheel 2.5 project.

## Table of Contents

1. [Docker Deployment](#docker-deployment)
2. [Kubernetes Deployment](#kubernetes-deployment)
3. [CI/CD Pipeline](#cicd-pipeline)
4. [Monitoring Setup](#monitoring-setup)
5. [Environment Configuration](#environment-configuration)

## Docker Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

### Quick Start

1. Clone the repository:
```bash
git clone https://github.com/your-org/salesboost.git
cd salesboost
```

2. Create environment file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start services:
```bash
cd deployment/docker
docker-compose up -d
```

4. Verify deployment:
```bash
docker-compose ps
curl http://localhost:8000/health
```

### Services

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Helm 3.0+ (optional)

### Deploy to Kubernetes

1. Create namespace:
```bash
kubectl create namespace salesboost
```

2. Create secrets:
```bash
kubectl create secret generic salesboost-secrets \
  --from-literal=database-url="postgresql://..." \
  --from-literal=redis-url="redis://..." \
  --from-literal=openai-api-key="sk-..." \
  -n salesboost
```

3. Deploy application:
```bash
kubectl apply -f deployment/kubernetes/deployment.yaml -n salesboost
```

4. Verify deployment:
```bash
kubectl get pods -n salesboost
kubectl get services -n salesboost
```

### Scaling

Horizontal Pod Autoscaler is configured to scale based on CPU and memory:

```bash
kubectl get hpa -n salesboost
```

Manual scaling:
```bash
kubectl scale deployment salesboost-backend --replicas=5 -n salesboost
```

## CI/CD Pipeline

### GitHub Actions

The CI/CD pipeline is configured in `.github/workflows/ci-cd.yml`.

#### Pipeline Stages

1. **Test**: Run unit and integration tests
2. **Build**: Build Docker images
3. **Security Scan**: Scan for vulnerabilities
4. **Deploy**: Deploy to production (main branch only)

#### Required Secrets

Configure these secrets in GitHub repository settings:

- `KUBE_CONFIG`: Base64-encoded kubeconfig
- `VITE_API_URL`: Frontend API URL
- `VITE_SUPABASE_URL`: Supabase URL
- `VITE_SUPABASE_KEY`: Supabase API key

#### Triggering Deployment

Push to main branch:
```bash
git push origin main
```

## Monitoring Setup

### Prometheus

Prometheus is configured to scrape metrics from:
- Backend API (`/metrics`)
- Node exporter
- Redis exporter

Access Prometheus: http://localhost:9090

### Grafana

Pre-configured dashboards for:
- Application metrics
- System metrics
- Business metrics

Default credentials:
- Username: admin
- Password: (set in GRAFANA_PASSWORD env var)

Access Grafana: http://localhost:3001

### Key Metrics

- Request rate and latency
- Error rate
- Active sessions
- LLM API calls and costs
- Database query performance

## Environment Configuration

### Backend Environment Variables

```bash
# Application
ENV_STATE=production
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis
REDIS_URL=redis://host:6379
REDIS_PASSWORD=your-password

# LLM APIs
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...

# Supabase
SUPABASE_URL=https://...
SUPABASE_KEY=...
SUPABASE_JWT_SECRET=...
```

### Frontend Environment Variables

```bash
VITE_API_URL=https://api.salesboost.example.com
VITE_SUPABASE_URL=https://...
VITE_SUPABASE_KEY=...
```

## Health Checks

### Backend Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "system_health": {
    "database": true,
    "redis": true,
    "llm": true
  }
}
```

### Frontend Health Check

```bash
curl http://localhost:3000/health
```

## Troubleshooting

### Backend not starting

1. Check logs:
```bash
docker-compose logs backend
```

2. Verify environment variables:
```bash
docker-compose exec backend env
```

3. Check database connection:
```bash
docker-compose exec backend python -c "from app.core.database import engine; print(engine.url)"
```

### Frontend build fails

1. Check Node version:
```bash
node --version  # Should be 18+
```

2. Clear cache and rebuild:
```bash
cd frontend
rm -rf node_modules dist
npm install
npm run build
```

### Kubernetes pods not ready

1. Check pod status:
```bash
kubectl describe pod <pod-name> -n salesboost
```

2. Check logs:
```bash
kubectl logs <pod-name> -n salesboost
```

3. Check events:
```bash
kubectl get events -n salesboost --sort-by='.lastTimestamp'
```

## Performance Tuning

### Backend

- Adjust worker count in Dockerfile:
```dockerfile
CMD ["uvicorn", "main:app", "--workers", "4"]
```

- Configure connection pools in settings
- Enable Redis caching for frequently accessed data

### Frontend

- Enable CDN for static assets
- Configure nginx caching
- Optimize bundle size with code splitting

## Security Best Practices

1. Use secrets management (Kubernetes Secrets, AWS Secrets Manager)
2. Enable HTTPS with valid certificates
3. Configure CORS properly
4. Implement rate limiting
5. Regular security updates
6. Enable audit logging

## Backup and Recovery

### Database Backup

```bash
# Backup
pg_dump -h localhost -U user -d salesboost > backup.sql

# Restore
psql -h localhost -U user -d salesboost < backup.sql
```

### Redis Backup

Redis persistence is enabled with AOF (Append Only File).

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/salesboost/issues
- Documentation: https://docs.salesboost.example.com
- Email: support@salesboost.example.com
