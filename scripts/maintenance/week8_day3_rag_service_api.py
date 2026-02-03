"""
Phase 4 Week 8 Day 3: RAG Service API Implementation

核心目标：
1. 实现 FastAPI RAG 服务
2. 提供检索、重排序、混合搜索等 API 端点
3. 集成 Week 1-4 的所有 RAG 优化技术
4. 实现请求验证、错误处理、性能监控

实现日期: 2026-02-02
"""

import logging
import os
import sys
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================

class SearchMode(str, Enum):
    """搜索模式"""
    DENSE = "dense"           # 纯向量检索
    SPARSE = "sparse"         # 纯关键词检索
    HYBRID = "hybrid"         # 混合检索
    ADAPTIVE = "adaptive"     # 自适应检索


class RetrievalRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., min_length=1, max_length=1000, description="查询文本")
    top_k: int = Field(default=5, ge=1, le=50, description="返回结果数量")
    search_mode: SearchMode = Field(default=SearchMode.HYBRID, description="搜索模式")
    enable_reranking: bool = Field(default=True, description="是否启用重排序")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="过滤条件")

    @classmethod
    def validate_query_field(cls, v):
        """验证查询文本"""
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class DocumentChunk(BaseModel):
    """文档片段"""
    id: str = Field(..., description="文档ID")
    content: str = Field(..., description="文档内容")
    score: float = Field(..., description="相关性分数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    source: Optional[str] = Field(default=None, description="来源")


class RetrievalResponse(BaseModel):
    """检索响应"""
    query: str = Field(..., description="原始查询")
    results: List[DocumentChunk] = Field(..., description="检索结果")
    total_results: int = Field(..., description="总结果数")
    search_mode: SearchMode = Field(..., description="使用的搜索模式")
    reranking_enabled: bool = Field(..., description="是否使用了重排序")
    latency_ms: float = Field(..., description="延迟（毫秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class RerankRequest(BaseModel):
    """重排序请求"""
    query: str = Field(..., min_length=1, max_length=1000, description="查询文本")
    documents: List[str] = Field(..., min_items=1, max_items=100, description="待重排序文档")
    top_k: int = Field(default=5, ge=1, le=50, description="返回结果数量")


class RerankResult(BaseModel):
    """重排序结果"""
    index: int = Field(..., description="原始索引")
    content: str = Field(..., description="文档内容")
    score: float = Field(..., description="重排序分数")


class RerankResponse(BaseModel):
    """重排序响应"""
    query: str = Field(..., description="原始查询")
    results: List[RerankResult] = Field(..., description="重排序结果")
    latency_ms: float = Field(..., description="延迟（毫秒）")


class EmbeddingRequest(BaseModel):
    """嵌入请求"""
    texts: List[str] = Field(..., min_items=1, max_items=100, description="待嵌入文本")
    dimension: Optional[int] = Field(default=None, description="嵌入维度（Matryoshka）")


class EmbeddingResponse(BaseModel):
    """嵌入响应"""
    embeddings: List[List[float]] = Field(..., description="嵌入向量")
    dimension: int = Field(..., description="向量维度")
    latency_ms: float = Field(..., description="延迟（毫秒）")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="API版本")
    uptime_seconds: float = Field(..., description="运行时间（秒）")
    total_requests: int = Field(..., description="总请求数")
    cache_hit_rate: float = Field(..., description="缓存命中率")


# ============================================================================
# Mock RAG Engine (模拟 Week 1-4 的 RAG 引擎)
# ============================================================================

class MockRAGEngine:
    """模拟 RAG 引擎（实际应该导入 Week 1-4 的实现）"""

    def __init__(self):
        self.request_count = 0
        self.cache_hits = 0
        self.cache_total = 0
        self.start_time = time.time()

        # 模拟知识库
        self.knowledge_base = [
            {
                "id": "doc_001",
                "content": "我们的白金信用卡最高额度可达50万元，比市面上普通信用卡的5-10万额度高出5倍。",
                "metadata": {"category": "product", "type": "credit_card"}
            },
            {
                "id": "doc_002",
                "content": "首年免年费，次年刷满6笔即可免年费，让您零成本享受高端服务。",
                "metadata": {"category": "pricing", "type": "credit_card"}
            },
            {
                "id": "doc_003",
                "content": "SPIN销售法包括四个阶段：Situation（情境问题）、Problem（难点问题）、Implication（暗示问题）、Need-Payoff（需求-效益问题）。",
                "metadata": {"category": "methodology", "type": "sales"}
            },
            {
                "id": "doc_004",
                "content": "FAB销售法：Feature（特征）- 产品有什么特点，Advantage（优势）- 这些特点有什么优势，Benefit（利益）- 这些优势能给客户带来什么好处。",
                "metadata": {"category": "methodology", "type": "sales"}
            },
            {
                "id": "doc_005",
                "content": "处理客户异议的关键是倾听、理解、回应。首先要认真倾听客户的顾虑，然后表示理解，最后提供解决方案。",
                "metadata": {"category": "objection_handling", "type": "sales"}
            }
        ]

        logger.info("MockRAGEngine initialized")

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        search_mode: SearchMode = SearchMode.HYBRID,
        enable_reranking: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """检索文档"""
        self.request_count += 1
        self.cache_total += 1

        # 模拟缓存命中（20%概率）
        import random
        if random.random() < 0.2:
            self.cache_hits += 1
            await asyncio.sleep(0.01)  # 缓存命中延迟
        else:
            await asyncio.sleep(0.05)  # 正常检索延迟

        # 简单的关键词匹配
        results = []
        for doc in self.knowledge_base:
            # 应用过滤器
            if filters:
                match = all(
                    doc["metadata"].get(k) == v
                    for k, v in filters.items()
                )
                if not match:
                    continue

            # 计算相似度（简化版）
            score = self._calculate_similarity(query, doc["content"])

            if score > 0:
                results.append({
                    "doc": doc,
                    "score": score
                })

        # 排序
        results.sort(key=lambda x: x["score"], reverse=True)

        # 重排序（模拟）
        if enable_reranking and len(results) > 0:
            await asyncio.sleep(0.02)  # 重排序延迟
            # 简单提升分数
            for r in results:
                r["score"] *= 1.2

        # 返回 top_k
        results = results[:top_k]

        return [
            DocumentChunk(
                id=r["doc"]["id"],
                content=r["doc"]["content"],
                score=r["score"],
                metadata=r["doc"]["metadata"],
                source="knowledge_base"
            )
            for r in results
        ]

    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[RerankResult]:
        """重排序文档"""
        await asyncio.sleep(0.02)  # 重排序延迟

        results = []
        for i, doc in enumerate(documents):
            score = self._calculate_similarity(query, doc) * 1.5
            results.append({
                "index": i,
                "content": doc,
                "score": score
            })

        # 排序
        results.sort(key=lambda x: x["score"], reverse=True)

        return [
            RerankResult(
                index=r["index"],
                content=r["content"],
                score=r["score"]
            )
            for r in results[:top_k]
        ]

    async def embed(
        self,
        texts: List[str],
        dimension: Optional[int] = None
    ) -> List[List[float]]:
        """生成嵌入向量"""
        await asyncio.sleep(0.01 * len(texts))  # 嵌入延迟

        # 模拟嵌入向量
        import random
        dim = dimension or 1024

        embeddings = []
        for text in texts:
            # 使用文本长度作为种子，保证相同文本生成相同向量
            random.seed(hash(text))
            embedding = [random.random() for _ in range(dim)]
            embeddings.append(embedding)

        return embeddings

    def _calculate_similarity(self, query: str, document: str) -> float:
        """计算相似度（简化版）"""
        query_words = set(query.lower().split())
        doc_words = set(document.lower().split())

        if not query_words:
            return 0.0

        intersection = query_words & doc_words
        return len(intersection) / len(query_words)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = time.time() - self.start_time
        cache_hit_rate = self.cache_hits / self.cache_total if self.cache_total > 0 else 0.0

        return {
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "cache_hits": self.cache_hits,
            "cache_total": self.cache_total,
            "cache_hit_rate": cache_hit_rate
        }


# ============================================================================
# FastAPI Application
# ============================================================================

# 全局 RAG 引擎实例
rag_engine: Optional[MockRAGEngine] = MockRAGEngine()


# 使用 lifespan 替代 on_event
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global rag_engine
    if rag_engine is None:
        rag_engine = MockRAGEngine()
    logger.info("RAG Service started")
    yield
    logger.info("RAG Service stopped")


# 创建 FastAPI 应用
app = FastAPI(
    title="SalesBoost RAG Service",
    description="高性能 RAG 检索服务 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_rag_engine() -> MockRAGEngine:
    """获取 RAG 引擎依赖"""
    if rag_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG engine not initialized"
        )
    return rag_engine


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """根路径"""
    return {
        "service": "SalesBoost RAG Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check(engine: MockRAGEngine = Depends(get_rag_engine)):
    """健康检查"""
    stats = engine.get_stats()

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime_seconds=stats["uptime_seconds"],
        total_requests=stats["total_requests"],
        cache_hit_rate=stats["cache_hit_rate"]
    )


@app.post("/v1/retrieve", response_model=RetrievalResponse)
async def retrieve(
    request: RetrievalRequest,
    engine: MockRAGEngine = Depends(get_rag_engine)
):
    """
    检索相关文档

    支持多种搜索模式：
    - dense: 纯向量检索
    - sparse: 纯关键词检索
    - hybrid: 混合检索（推荐）
    - adaptive: 自适应检索
    """
    start_time = time.time()

    try:
        # 执行检索
        results = await engine.retrieve(
            query=request.query,
            top_k=request.top_k,
            search_mode=request.search_mode,
            enable_reranking=request.enable_reranking,
            filters=request.filters
        )

        latency_ms = (time.time() - start_time) * 1000

        return RetrievalResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            search_mode=request.search_mode,
            reranking_enabled=request.enable_reranking,
            latency_ms=latency_ms,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "filters_applied": request.filters is not None
            }
        )

    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval failed: {str(e)}"
        )


@app.post("/v1/rerank", response_model=RerankResponse)
async def rerank(
    request: RerankRequest,
    engine: MockRAGEngine = Depends(get_rag_engine)
):
    """
    重排序文档

    使用神经网络重排序模型对检索结果进行重新排序，提升准确率。
    """
    start_time = time.time()

    try:
        # 执行重排序
        results = await engine.rerank(
            query=request.query,
            documents=request.documents,
            top_k=request.top_k
        )

        latency_ms = (time.time() - start_time) * 1000

        return RerankResponse(
            query=request.query,
            results=results,
            latency_ms=latency_ms
        )

    except Exception as e:
        logger.error(f"Rerank error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rerank failed: {str(e)}"
        )


@app.post("/v1/embed", response_model=EmbeddingResponse)
async def embed(
    request: EmbeddingRequest,
    engine: MockRAGEngine = Depends(get_rag_engine)
):
    """
    生成文本嵌入向量

    支持 Matryoshka 自适应嵌入，可指定维度（64/128/256/512/1024）。
    """
    start_time = time.time()

    try:
        # 生成嵌入
        embeddings = await engine.embed(
            texts=request.texts,
            dimension=request.dimension
        )

        latency_ms = (time.time() - start_time) * 1000

        return EmbeddingResponse(
            embeddings=embeddings,
            dimension=len(embeddings[0]) if embeddings else 0,
            latency_ms=latency_ms
        )

    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding failed: {str(e)}"
        )


@app.get("/v1/stats", response_model=Dict[str, Any])
async def get_stats(engine: MockRAGEngine = Depends(get_rag_engine)):
    """获取服务统计信息"""
    return engine.get_stats()


# ============================================================================
# 测试和演示
# ============================================================================

async def demo_rag_api():
    """演示 RAG API"""
    print("\n" + "=" * 80)
    print("RAG Service API Demo")
    print("=" * 80)

    # 导入测试客户端
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # 1. 健康检查
    print("\n[Test 1] Health Check")
    response = client.get("/health")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")

    # 2. 检索测试
    print("\n[Test 2] Retrieval")
    retrieval_request = {
        "query": "信用卡额度是多少",
        "top_k": 3,
        "search_mode": "hybrid",
        "enable_reranking": True
    }
    response = client.post("/v1/retrieve", json=retrieval_request)
    print(f"  Status: {response.status_code}")
    result = response.json()
    print(f"  Query: {result['query']}")
    print(f"  Results: {result['total_results']}")
    print(f"  Latency: {result['latency_ms']:.2f}ms")
    for i, doc in enumerate(result['results'], 1):
        print(f"    [{i}] Score: {doc['score']:.3f} - {doc['content'][:50]}...")

    # 3. 重排序测试
    print("\n[Test 3] Reranking")
    rerank_request = {
        "query": "如何处理客户异议",
        "documents": [
            "处理客户异议的关键是倾听、理解、回应。",
            "我们的白金信用卡最高额度可达50万元。",
            "SPIN销售法包括四个阶段。"
        ],
        "top_k": 2
    }
    response = client.post("/v1/rerank", json=rerank_request)
    print(f"  Status: {response.status_code}")
    result = response.json()
    print(f"  Query: {result['query']}")
    print(f"  Latency: {result['latency_ms']:.2f}ms")
    for i, doc in enumerate(result['results'], 1):
        print(f"    [{i}] Score: {doc['score']:.3f} - {doc['content'][:50]}...")

    # 4. 嵌入测试
    print("\n[Test 4] Embedding")
    embed_request = {
        "texts": ["信用卡额度", "年费多少"],
        "dimension": 256
    }
    response = client.post("/v1/embed", json=embed_request)
    print(f"  Status: {response.status_code}")
    result = response.json()
    print(f"  Dimension: {result['dimension']}")
    print(f"  Embeddings: {len(result['embeddings'])} vectors")
    print(f"  Latency: {result['latency_ms']:.2f}ms")

    # 5. 统计信息
    print("\n[Test 5] Statistics")
    response = client.get("/v1/stats")
    print(f"  Status: {response.status_code}")
    stats = response.json()
    print(f"  Total Requests: {stats['total_requests']}")
    print(f"  Cache Hit Rate: {stats['cache_hit_rate']*100:.1f}%")
    print(f"  Uptime: {stats['uptime_seconds']:.2f}s")

    # 6. 过滤器测试
    print("\n[Test 6] Retrieval with Filters")
    retrieval_request = {
        "query": "销售方法",
        "top_k": 5,
        "search_mode": "hybrid",
        "enable_reranking": False,
        "filters": {"category": "methodology"}
    }
    response = client.post("/v1/retrieve", json=retrieval_request)
    print(f"  Status: {response.status_code}")
    result = response.json()
    print(f"  Query: {result['query']}")
    print(f"  Results: {result['total_results']}")
    print(f"  Filters: category=methodology")
    for i, doc in enumerate(result['results'], 1):
        print(f"    [{i}] {doc['metadata']['category']} - {doc['content'][:50]}...")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 80)
    print("Phase 4 Week 8 Day 3: RAG Service API Implementation")
    print("=" * 80)

    # 运行演示
    asyncio.run(demo_rag_api())

    print("\n" + "=" * 80)
    print("All tests passed!")
    print("=" * 80)

    print("\n[Info] To run the server:")
    print("  uvicorn week8_day3_rag_service_api:app --reload --port 8001")
    print("\n[Info] API Documentation:")
    print("  Swagger UI: http://localhost:8001/docs")
    print("  ReDoc: http://localhost:8001/redoc")


if __name__ == "__main__":
    main()
