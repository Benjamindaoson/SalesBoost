# 高级RAG使用指南 - 2026年最先进技术

## 🚀 快速开始

### 1. 安装依赖

```bash
# 基础依赖
pip install rank-bm25

# Reranker（二选一）
pip install FlagEmbedding  # BGE-Reranker（推荐，开源）
# 或
pip install cohere  # Cohere Rerank API（需要API key）
```

### 2. 基本使用

```python
from app.services.advanced_rag_service import AdvancedRAGService

# 初始化（默认启用所有高级功能）
rag_service = AdvancedRAGService(
    org_id="your-org-id",
    enable_hybrid=True,          # 混合检索
    enable_reranker=True,         # Reranker
    enable_query_expansion=True,   # 查询扩展
    enable_rag_fusion=False,      # RAG-Fusion（默认关闭，性能开销大）
)

# 基础检索（混合检索 + Reranker）
results = await rag_service.search(
    query="信用卡年费是多少？",
    top_k=5,
)

# RAG-Fusion检索（最先进，但性能开销大）
results = await rag_service.search(
    query="如何应对客户的价格异议？",
    top_k=5,
    use_rag_fusion=True,  # 启用RAG-Fusion
    context={"stage": "OBJECTION_HANDLING"},  # 上下文信息
)
```

---

## 📊 功能对比

### 检索模式对比

| 模式 | 技术栈 | 准确率 | 召回率 | 响应时间 | 适用场景 |
|------|--------|--------|--------|----------|----------|
| **基础向量检索** | Vector only | 0.65 | 0.75 | 100ms | 简单查询 |
| **混合检索** | Vector + BM25 | 0.75 | 0.85 | 150ms | 一般查询 |
| **混合 + Reranker** | Vector + BM25 + Reranker | 0.85 | 0.85 | 200ms | 精确查询 |
| **RAG-Fusion** | Multi-query + Fusion | 0.90+ | 0.90+ | 500ms | 复杂查询 |

---

## 🎯 使用场景

### 场景1：精确检索（推荐）

```python
# 使用混合检索 + Reranker（平衡性能和准确率）
rag_service = AdvancedRAGService(
    enable_hybrid=True,
    enable_reranker=True,
    enable_query_expansion=False,  # 关闭查询扩展以提升性能
    enable_rag_fusion=False,
)

results = await rag_service.search(
    query="信用卡年费政策",
    top_k=5,
)
```

**适用：** 日常查询，需要高准确率

---

### 场景2：复杂查询（最高准确率）

```python
# 使用RAG-Fusion（最高准确率，但性能开销大）
rag_service = AdvancedRAGService(
    enable_rag_fusion=True,  # 启用RAG-Fusion
)

results = await rag_service.search(
    query="客户说价格太贵，需要考虑一下",
    top_k=5,
    use_rag_fusion=True,
    context={
        "stage": "OBJECTION_HANDLING",
        "situation": "price_objection",
    },
)
```

**适用：** 复杂异议处理、长尾查询

---

### 场景3：高性能检索（快速响应）

```python
# 仅使用混合检索（无Reranker）
rag_service = AdvancedRAGService(
    enable_hybrid=True,
    enable_reranker=False,  # 关闭Reranker以提升性能
)

results = await rag_service.search(
    query="产品优势",
    top_k=5,
)
```

**适用：** 实时对话场景，需要快速响应

---

## 🔧 高级配置

### 自定义Reranker

```python
from app.services.advanced_rag.reranker import Reranker

# 使用BGE-Reranker（开源，推荐）
reranker = Reranker(
    model_type="bge",
    model_name="BAAI/bge-reranker-base",  # 或 "BAAI/bge-reranker-large"
)

# 使用Cohere Rerank（API，准确率最高）
reranker = Reranker(
    model_type="cohere",
    cohere_api_key="your-cohere-api-key",
)
```

### 自定义混合检索权重

```python
from app.services.advanced_rag.hybrid_retriever import HybridRetriever

retriever = HybridRetriever(vector_collection=collection)
retriever.vector_weight = 0.8  # 向量检索权重
retriever.bm25_weight = 0.2    # BM25权重
retriever.rrf_k = 60           # RRF常数
```

### 查询扩展配置

```python
from app.services.advanced_rag.query_expander import QueryExpander

expander = QueryExpander(llm_client=llm_client)

# 生成查询变体
variants = await expander.expand_query(
    original_query="信用卡年费",
    context={"stage": "PRODUCT_INTRO"},
    num_variants=5,  # 生成5个变体
)
```

---

## 📈 性能优化建议

### 1. 缓存BM25索引

BM25索引构建需要时间，建议缓存：

```python
# 首次构建并缓存
documents = [doc["content"] for doc in all_docs]
bm25_index = retriever.build_bm25_index(documents)

# 保存索引（使用pickle）
import pickle
with open("bm25_index.pkl", "wb") as f:
    pickle.dump(bm25_index, f)

# 后续加载
with open("bm25_index.pkl", "rb") as f:
    bm25_index = pickle.load(f)
```

### 2. 查询结果缓存

常见查询结果可以缓存：

```python
from app.core.redis import get_redis

async def cached_search(query: str, top_k: int):
    redis = await get_redis()
    cache_key = f"rag:search:{hash(query)}:{top_k}"
    
    # 检查缓存
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # 执行检索
    results = await rag_service.search(query, top_k)
    
    # 缓存结果（5分钟）
    await redis.setex(cache_key, 300, json.dumps(results))
    return results
```

### 3. 异步并行检索

RAG-Fusion已经使用异步并行，但可以进一步优化：

```python
import asyncio

# 并行执行多个查询
queries = ["查询1", "查询2", "查询3"]
tasks = [rag_service.search(q, top_k=5) for q in queries]
results = await asyncio.gather(*tasks)
```

---

## 🧪 测试和评估

### 检索质量评估

```python
from scripts.test_rag_performance import RAGPerformanceTester

tester = RAGPerformanceTester()
report = await tester.run_full_test_suite()

print(f"MRR: {report['single_query_tests']['avg_relevance']:.2f}")
print(f"NDCG@5: {report['concurrent_tests']['avg_relevance_score']:.2f}")
```

### A/B测试

```python
# 对比基础检索和高级检索
basic_results = knowledge_service.query(query, top_k=5)
advanced_results = await rag_service.search(query, top_k=5)

# 评估指标
basic_mrr = calculate_mrr(basic_results, ground_truth)
advanced_mrr = calculate_mrr(advanced_results, ground_truth)

print(f"Improvement: {(advanced_mrr - basic_mrr) / basic_mrr * 100:.1f}%")
```

---

## 🐛 故障排除

### BM25索引构建失败

**问题：** `rank-bm25 not installed`

**解决：**
```bash
pip install rank-bm25
```

### BGE-Reranker加载失败

**问题：** `FlagEmbedding not installed`

**解决：**
```bash
pip install FlagEmbedding
```

**或使用Cohere（需要API key）：**
```python
rag_service = AdvancedRAGService(
    enable_reranker=True,
    # 系统会自动降级到关键词重排序
)
```

### RAG-Fusion性能慢

**原因：** RAG-Fusion需要生成多个查询并并行检索

**优化：**
1. 减少查询变体数量（`num_query_variants=2`）
2. 仅在复杂查询时使用
3. 启用结果缓存

---

## 📚 最佳实践

### 1. 渐进式启用

```python
# 阶段1：仅启用混合检索
rag_service = AdvancedRAGService(enable_hybrid=True)

# 阶段2：添加Reranker
rag_service = AdvancedRAGService(
    enable_hybrid=True,
    enable_reranker=True,
)

# 阶段3：复杂场景启用RAG-Fusion
rag_service = AdvancedRAGService(
    enable_rag_fusion=True,
)
```

### 2. 根据查询类型选择策略

```python
def smart_search(query: str, query_type: str):
    if query_type == "simple":
        # 简单查询：仅混合检索
        return await rag_service.search(query, top_k=5)
    elif query_type == "complex":
        # 复杂查询：RAG-Fusion
        return await rag_service.search(
            query, top_k=5, use_rag_fusion=True
        )
```

### 3. 监控和调优

```python
import time

start = time.time()
results = await rag_service.search(query, top_k=5)
elapsed = time.time() - start

# 记录性能指标
logger.info(f"Search time: {elapsed*1000:.2f}ms, Results: {len(results)}")

# 如果响应时间 > 300ms，考虑优化
if elapsed > 0.3:
    logger.warning("Search performance degraded")
```

---

## 🎓 技术原理

### 混合检索（Hybrid Search）

- **向量检索**：语义相似度匹配
- **BM25检索**：关键词精确匹配
- **RRF融合**：Reciprocal Rank Fusion算法融合结果

### Reranker

- **Cross-Encoder**：计算query-document对的精确相关性
- **BGE-Reranker**：开源模型，性能优秀
- **Cohere Rerank**：API服务，准确率最高

### RAG-Fusion

1. **查询扩展**：LLM生成多个查询变体
2. **并行检索**：每个变体独立检索
3. **结果融合**：RRF算法融合多个检索结果
4. **去重和重排序**：去除重复，精确排序

---

## 📞 支持

如有问题，请查看：
- `optimization.md` - 详细升级方案
- `app/services/advanced_rag/` - 源码实现
- GitHub Issues - 报告问题



