# Environment Configuration Guide

## Quick Start

### 1. Create Your Local Environment File

```bash
# Copy the example file
cp .env.example .env

# Edit with your actual values
nano .env  # or use your preferred editor
```

### 2. Required Configuration

**Minimum required for development:**
```bash
# Database (SQLite for development)
DATABASE_URL=sqlite+aiosqlite:///./salesboost.db

# LLM Provider (at least one required)
SILICONFLOW_API_KEY=sk-your-key-here
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

# Vector Store
QDRANT_URL=http://localhost:6333

# Security
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
```

**For PDF OCR processing:**
```bash
DASHSCOPE_API_KEY=sk-your-dashscope-key-here
```

### 3. Production Deployment

For production, create `.env.production` with:

```bash
# Copy example as starting point
cp .env.example .env.production

# Edit with production values
nano .env.production
```

**Critical production settings:**
- Use PostgreSQL instead of SQLite
- Set `ENV_STATE=production`
- Set `DEBUG=false`
- Use strong `SECRET_KEY` (64+ characters)
- Configure proper CORS origins
- Enable monitoring and observability

## File Structure

```
.env.example          # Template file (committed to git)
.env                  # Local development (NOT committed)
.env.production       # Production config (NOT committed)
```

## Configuration Sections

### Core Settings
- `ENV_STATE`: Environment (development/staging/production)
- `DEBUG`: Debug mode (true/false)
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)

### Database
- **Development**: SQLite (`sqlite+aiosqlite:///./salesboost.db`)
- **Production**: PostgreSQL (`postgresql+asyncpg://user:pass@host:5432/db`)

### LLM Providers
- **SiliconFlow**: DeepSeek models (required)
- **OpenAI**: GPT models (optional)
- **Google**: Gemini models (optional)
- **DashScope**: Qwen-VL-OCR for PDF processing (optional)

### Vector Store
- **Qdrant**: Vector database for RAG
- Local: `http://localhost:6333`
- Cloud: `https://your-cluster.qdrant.io`

### Feature Flags
- `AGENTIC_V3_ENABLED`: Enable v3 agent system
- `BANDIT_ROUTING_ENABLED`: Enable multi-armed bandit routing
- `RAG_HYBRID_ENABLED`: Enable hybrid RAG (dense + sparse)
- `BGE_RERANKER_ENABLED`: Enable BGE reranker

### Coordinator Engine
Choose orchestration engine:
- `legacy`: MVP Orchestrator (stable)
- `workflow`: WorkflowCoordinator with AI intent
- `langgraph`: LangGraphCoordinator (recommended)

## Security Best Practices

### 1. Never Commit Secrets
The `.gitignore` is configured to exclude:
- `.env`
- `.env.local`
- `.env.production`
- `.env.*.local`

Only `.env.example` is committed (contains no secrets).

### 2. Generate Strong Keys
```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate password hash
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your-password'))"
```

### 3. Rotate Keys Regularly
- Rotate API keys every 90 days
- Rotate SECRET_KEY on security incidents
- Use different keys for dev/staging/production

### 4. Use Environment Variables in Production
Instead of `.env.production` file, use:
- Docker secrets
- Kubernetes secrets
- AWS Secrets Manager
- HashiCorp Vault

## Validation

### Check Configuration
```bash
# Verify all required variables are set
python -c "from core.config import settings; print(settings.dict())"

# Test database connection
python -c "from core.database import engine; print('DB OK')"

# Test LLM provider
python scripts/ops/verify_siliconflow.py
```

### Common Issues

**Issue: Missing API key**
```
ValueError: SILICONFLOW_API_KEY not found in environment variables
```
**Solution:** Add the key to your `.env` file

**Issue: Database connection failed**
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Solution:** Check DATABASE_URL and ensure PostgreSQL is running

**Issue: Qdrant connection failed**
```
httpx.ConnectError: [Errno 111] Connection refused
```
**Solution:** Start Qdrant with `docker-compose up qdrant`

## Migration from Old Config

If you have old configuration files:

```bash
# Backup old files
mv .env .env.backup
mv .env.feature_flags .env.feature_flags.backup

# Create new config from example
cp .env.example .env

# Manually copy your values from backup to new .env
```

## Environment-Specific Examples

### Development
```bash
ENV_STATE=development
DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///./salesboost.db
QDRANT_URL=http://localhost:6333
COORDINATOR_ENGINE=langgraph
```

### Staging
```bash
ENV_STATE=staging
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:pass@staging-db:5432/salesboost
QDRANT_URL=http://qdrant-staging:6333
COORDINATOR_ENGINE=langgraph
AB_TESTING_ENABLED=true
```

### Production
```bash
ENV_STATE=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/salesboost
QDRANT_URL=https://prod-cluster.qdrant.io
COORDINATOR_ENGINE=langgraph
PROMETHEUS_ENABLED=true
SENTRY_DSN=https://your-sentry-dsn
```

## Support

For configuration issues:
1. Check this guide
2. Review `.env.example` for all available options
3. Check application logs: `tail -f logs/app.log`
4. Verify with validation scripts in `scripts/ops/`

---

**Last Updated:** 2026-02-01
**Version:** 1.0
