# SalesBoost Knowledge Base Deployment Guide

## Overview

This guide covers deploying the SalesBoost knowledge base system to production.

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ (production) or SQLite (development)
- 2GB+ RAM
- 10GB+ disk space

## Quick Start

### 1. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd SalesBoost

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r config/python/requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Key variables:
# - DATABASE_URL: PostgreSQL connection string
# - DEEPSEEK_API_KEY: For data generation (optional)
# - SILICONFLOW_API_KEY: For embeddings (optional)
```

### 3. Initialize Knowledge Base

```bash
# Step 1: Setup local environment
python scripts/setup_local_environment.py

# Step 2: Process sales data
python scripts/process_sales_data.py

# Step 3: Generate training data (optional, requires API key)
python scripts/generate_training_data.py

# Step 4: Create semantic chunks
python scripts/smart_chunking.py

# Step 5: Create agent interface
python scripts/create_agent_interface.py
```

### 4. Verify Installation

```bash
# Test knowledge integration
python app/knowledge_integration.py

# Expected output:
# [OK] Knowledge integration initialized successfully
# [OK] All tests passed!
```

## Production Deployment

### Option 1: Docker Deployment

```bash
# Build production image
docker build -f Dockerfile.production -t salesboost:latest .

# Run container
docker run -d \
  --name salesboost \
  -p 8000:8000 \
  --env-file .env.production \
  -v $(pwd)/storage:/app/storage \
  salesboost:latest
```

### Option 2: Manual Deployment

```bash
# 1. Setup production environment
export ENV_STATE=production
export DATABASE_URL="postgresql://user:pass@host:5432/salesboost"

# 2. Run database migrations
alembic upgrade head

# 3. Initialize knowledge base (one-time)
python scripts/setup_local_environment.py
python scripts/process_sales_data.py
python scripts/smart_chunking.py
python scripts/create_agent_interface.py

# 4. Start application
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Option 3: Cloud Platform (Render/Railway/Fly.io)

1. **Connect Repository**: Link your Git repository to the platform

2. **Configure Build Command**:
   ```bash
   pip install -r config/python/requirements.txt && \
   python scripts/setup_local_environment.py && \
   python scripts/process_sales_data.py && \
   python scripts/smart_chunking.py && \
   python scripts/create_agent_interface.py
   ```

3. **Configure Start Command**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4
   ```

4. **Set Environment Variables**:
   - `DATABASE_URL`: PostgreSQL connection string
   - `ENV_STATE`: production
   - `ALLOWED_HOSTS`: your-domain.com
   - Other variables from `.env.example`

## Knowledge Base Management

### Adding New Data

```bash
# 1. Add files to data directory
# - Excel files → 销冠能力复制数据库/产品权益/
# - PDF files → 销冠能力复制数据库/销售成交营销SOP和话术/
# - Word files → 销冠能力复制数据库/销售冠军成交经验分享/

# 2. Reprocess data
python scripts/process_sales_data.py

# 3. Regenerate chunks
python scripts/smart_chunking.py

# 4. Rebuild agent interface
python scripts/create_agent_interface.py
```

### Updating Knowledge Base

```bash
# Full rebuild (recommended for major changes)
python scripts/process_sales_data.py && \
python scripts/smart_chunking.py && \
python scripts/create_agent_interface.py

# Incremental update (for minor changes)
python scripts/smart_chunking.py && \
python scripts/create_agent_interface.py
```

## Integration with Agents

### Using Knowledge Integration in Agents

```python
from app.knowledge_integration import get_knowledge_integration

# In your agent code
ki = get_knowledge_integration()

# Search for relevant knowledge
knowledge = ki.search_knowledge(
    query="如何处理价格异议",
    agent_type="coach",
    top_k=5
)

# Format for LLM prompt
context = ki.format_knowledge_for_prompt(knowledge, max_length=2000)

# Use in your prompt
prompt = f"""
Based on the following knowledge:

{context}

Answer the user's question: {user_query}
"""
```

### Agent-Specific Methods

```python
# Coach Agent
results = ki.search_knowledge(query, agent_type="coach")

# Compliance Agent
results = ki.search_knowledge(query, agent_type="compliance")

# Practice Agent
scenarios = ki.get_training_scenarios(objection_type="price", limit=5)

# Get champion cases
cases = ki.get_champion_cases(limit=10)
```

## Monitoring and Maintenance

### Health Checks

```bash
# Check application health
curl http://localhost:8000/health

# Check knowledge base statistics
python -c "
from app.knowledge_integration import get_knowledge_integration
ki = get_knowledge_integration()
ki.initialize()
stats = ki.get_retriever().get_statistics()
print(f'Total chunks: {stats[\"total_chunks\"]}')
print(f'Chunks by type: {stats[\"chunks_by_type\"]}')
"
```

### Backup and Recovery

```bash
# Backup knowledge base
tar -czf knowledge_backup_$(date +%Y%m%d).tar.gz \
  storage/processed_data/ \
  storage/databases/ \
  data/seeds/

# Restore from backup
tar -xzf knowledge_backup_YYYYMMDD.tar.gz
```

### Performance Optimization

1. **Enable Caching**: Set `TOOL_CACHE_ENABLED=true` in `.env`

2. **Optimize Chunk Size**: Adjust in `scripts/smart_chunking.py`:
   ```python
   chunker = SmartChunker(
       chunk_size=512,  # Increase for longer context
       chunk_overlap=50,
       min_chunk_size=100
   )
   ```

3. **Add BGE-M3 Embeddings** (when ChromaDB DLL issues resolved):
   ```bash
   python scripts/build_knowledge_index.py
   ```

## Troubleshooting

### Issue: ChromaDB DLL Load Failed

**Solution**: Use file-based fallback (already implemented)
```python
# The system automatically falls back to file-based search
# No action needed - it works out of the box
```

### Issue: No Knowledge Results

**Solution**: Verify data processing
```bash
# Check if chunks exist
ls -lh storage/processed_data/semantic_chunks.json

# Verify chunk count
python -c "
import json
with open('storage/processed_data/semantic_chunks.json') as f:
    chunks = json.load(f)
    print(f'Total chunks: {len(chunks)}')
"
```

### Issue: Encoding Errors (Windows)

**Solution**: All scripts handle GBK encoding automatically
```python
# Scripts use [OK], [X], [WARN] instead of Unicode symbols
# No action needed
```

## Cost Optimization

### Current Setup (< $200/month)

- **Storage**: File-based (free)
- **Database**: SQLite (free) or PostgreSQL (Render: $7/month)
- **Compute**: Single server (Render: $7/month)
- **Embeddings**: File-based search (free)

### Optional Enhancements

- **DeepSeek API**: $0.001/1K tokens (~$10/month for 10M tokens)
- **BGE-M3 Embeddings**: Self-hosted (free) or API (~$20/month)
- **Vector Database**: ChromaDB self-hosted (free)

## Security Considerations

1. **Environment Variables**: Never commit `.env` files
2. **API Keys**: Use secrets management (e.g., Render secrets)
3. **Database**: Use SSL connections in production
4. **Access Control**: Implement authentication for API endpoints

## Next Steps

1. **Week 3 Tasks**:
   - ✅ Integration with existing agents (completed)
   - ⏳ Cloud deployment (ready to deploy)
   - ⏳ User testing (invite 10 seed users)

2. **Future Enhancements**:
   - Add BGE-M3 embeddings for better search
   - Implement semantic search with vector similarity
   - Add real-time data updates
   - Implement A/B testing for knowledge retrieval

## Support

For issues or questions:
1. Check logs: `tail -f logs/app.log`
2. Review configuration: `cat .env`
3. Test integration: `python app/knowledge_integration.py`

## Appendix: File Structure

```
SalesBoost/
├── app/
│   ├── knowledge_integration.py    # Integration module
│   ├── agents/                     # Existing agents
│   └── tools/                      # Tool implementations
├── scripts/
│   ├── setup_local_environment.py  # Environment setup
│   ├── process_sales_data.py       # Data processing
│   ├── generate_training_data.py   # Data generation
│   ├── smart_chunking.py           # Semantic chunking
│   └── create_agent_interface.py   # Agent interface
├── storage/
│   ├── databases/                  # SQLite database
│   ├── chromadb/                   # Vector database
│   ├── processed_data/             # Processed chunks
│   └── generated_data/             # Generated scenarios
├── data/
│   └── seeds/                      # Champion cases
└── 销冠能力复制数据库/              # Source data
    ├── 产品权益/                   # Product data
    ├── 销售成交营销SOP和话术/       # Sales SOPs
    └── 销售冠军成交经验分享/        # Champion cases
```

---

**Last Updated**: 2026-02-01
**Version**: 1.0.0
**Status**: Production Ready ✅
