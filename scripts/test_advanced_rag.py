"""
高级RAG完整测试脚本
测试所有2026年最先进功能
"""
import asyncio
import logging
from app.services.advanced_rag_service import AdvancedRAGService
from app.services.advanced_rag.evaluation_metrics import RetrievalMetrics
from app.services.advanced_rag.ab_testing import ABTestFramework
from app.services.advanced_rag.financial_config import get_financial_optimized_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_hybrid_search():
    """测试混合检索"""
    logger.info("=== Testing Hybrid Search ===")
    
    rag_service = AdvancedRAGService(
        enable_hybrid=True,
        enable_reranker=True,
        enable_query_expansion=False,
        financial_optimized=True,
    )
    
    # 构建BM25索引
    await rag_service.build_and_cache_bm25_index()
    
    results = await rag_service.search(
        query="信用卡年费是多少？",
        top_k=5,
    )
    
    logger.info(f"Hybrid search returned {len(results)} results")
    for i, r in enumerate(results[:3], 1):
        logger.info(f"  {i}. Score: {r.get('rerank_score', r.get('relevance_score', 0)):.3f}")
        logger.info(f"     Content: {r.get('content', '')[:100]}...")
    
    return results


async def test_adaptive_retrieval():
    """测试自适应检索"""
    logger.info("\n=== Testing Adaptive Retrieval ===")
    
    rag_service = AdvancedRAGService(
        enable_adaptive=True,
        financial_optimized=True,
    )
    
    # 事实性查询
    factual_results = await rag_service.search(
        query="信用卡年费费率",
        top_k=5,
        use_adaptive=True,
    )
    logger.info(f"Factual query: {len(factual_results)} results")
    
    # 异议处理查询
    objection_results = await rag_service.search(
        query="客户说价格太贵",
        top_k=5,
        use_adaptive=True,
        context={"stage": "OBJECTION_HANDLING"},
    )
    logger.info(f"Objection query: {len(objection_results)} results")
    
    return factual_results, objection_results


async def test_rag_fusion():
    """测试RAG-Fusion"""
    logger.info("\n=== Testing RAG-Fusion ===")
    
    rag_service = AdvancedRAGService(
        enable_rag_fusion=True,
        financial_optimized=True,
    )
    
    results = await rag_service.search(
        query="如何应对客户的价格异议？",
        top_k=5,
        use_rag_fusion=True,
        context={"stage": "OBJECTION_HANDLING"},
    )
    
    logger.info(f"RAG-Fusion returned {len(results)} results")
    return results


async def test_multi_vector():
    """测试多向量检索"""
    logger.info("\n=== Testing Multi-Vector Retrieval ===")
    
    rag_service = AdvancedRAGService(
        enable_multi_vector=True,
        financial_optimized=True,
    )
    
    results = await rag_service.search(
        query="信用卡产品对比",
        top_k=5,
        use_multi_vector=True,
    )
    
    logger.info(f"Multi-vector returned {len(results)} results")
    for r in results[:2]:
        if "parent_document" in r:
            logger.info(f"  Parent doc: {r['parent_document'].get('id', 'N/A')}")
            logger.info(f"  Combined score: {r.get('combined_score', 0):.3f}")
    
    return results


async def test_context_compression():
    """测试上下文压缩"""
    logger.info("\n=== Testing Context Compression ===")
    
    rag_service = AdvancedRAGService(
        enable_context_compression=True,
        financial_optimized=True,
    )
    
    results = await rag_service.search(
        query="信用卡年费政策详细说明",
        top_k=5,
        use_compression=True,
    )
    
    logger.info(f"Compressed results: {len(results)}")
    for r in results[:2]:
        ratio = r.get("compression_ratio", 1.0)
        logger.info(f"  Compression ratio: {ratio:.2f}")
        logger.info(f"  Content length: {len(r.get('content', ''))}")
    
    return results


async def test_ab_comparison():
    """测试A/B对比"""
    logger.info("\n=== Testing A/B Comparison ===")
    
    # 基础策略
    basic_service = AdvancedRAGService(
        enable_hybrid=False,
        enable_reranker=False,
        financial_optimized=False,
    )
    
    # 高级策略
    advanced_service = AdvancedRAGService(
        **get_financial_optimized_config()
    )
    
    ab_framework = ABTestFramework()
    
    strategies = [
        {
            "name": "Basic Vector",
            "retriever": basic_service,
            "config": {"top_k": 5},
        },
        {
            "name": "Advanced Hybrid + Reranker",
            "retriever": advanced_service,
            "config": {"top_k": 5},
        },
    ]
    
    comparison = await ab_framework.compare_strategies(
        query="信用卡年费是多少？",
        strategies=strategies,
    )
    
    logger.info("A/B Comparison Results:")
    for strategy in comparison["strategies"]:
        logger.info(f"  {strategy['name']}: {strategy.get('metrics', {})}")
    
    return comparison


async def test_evaluation_metrics():
    """测试评估指标"""
    logger.info("\n=== Testing Evaluation Metrics ===")
    
    rag_service = AdvancedRAGService(**get_financial_optimized_config())
    
    # 模拟测试用例
    test_cases = [
        {
            "query": "信用卡年费",
            "results": await rag_service.search("信用卡年费", top_k=5),
            "ground_truth": ["doc1", "doc2"],  # 假设的正确答案
        },
        {
            "query": "价格异议处理",
            "results": await rag_service.search("价格异议处理", top_k=5),
            "ground_truth": ["doc3"],
        },
    ]
    
    metrics = RetrievalMetrics.evaluate_batch(test_cases)
    
    logger.info("Evaluation Metrics:")
    logger.info(f"  Avg MRR: {metrics.get('avg_mrr', 0):.3f}")
    logger.info(f"  Avg NDCG@5: {metrics.get('avg_ndcg@5', 0):.3f}")
    logger.info(f"  Avg Precision@5: {metrics.get('avg_precision@5', 0):.3f}")
    logger.info(f"  Avg Financial Accuracy: {metrics.get('financial_accuracy', 0):.3f}")
    
    return metrics


async def main():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("Advanced RAG Complete Test Suite")
    logger.info("=" * 60)
    
    try:
        # 1. 混合检索
        await test_hybrid_search()
        
        # 2. 自适应检索
        await test_adaptive_retrieval()
        
        # 3. RAG-Fusion
        await test_rag_fusion()
        
        # 4. 多向量检索
        await test_multi_vector()
        
        # 5. 上下文压缩
        await test_context_compression()
        
        # 6. A/B对比
        await test_ab_comparison()
        
        # 7. 评估指标
        await test_evaluation_metrics()
        
        logger.info("\n" + "=" * 60)
        logger.info("All tests completed!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())


