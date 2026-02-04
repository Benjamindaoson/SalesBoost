#!/usr/bin/env python3
"""
Phase 3A Week 1.5: Optimized Cross-Encoder Reranking
TinyBERT-L-2-v2 优化版本 - 延迟从15s降到0.5s

性能目标:
- 延迟: 15s → 0.5s (30x提升)
- 准确率: 保持 >8.0 分
- 成本: 几乎免费 (CPU推理)

优化策略:
1. 模型: ms-marco-MiniLM-L-12-v2 (12层) → TinyBERT-L-2-v2 (2层)
2. 候选数: 50 → 15
3. 批处理: 单个预测 → 批量预测
"""

from sentence_transformers import CrossEncoder
import requests
from typing import List, Dict
import time


class OptimizedNeuralReranker:
    """2026年优化版神经重排序器 - 6x速度提升"""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-TinyBERT-L-2-v2"):
        """
        初始化优化版重排序器

        Args:
            model_name: Cross-Encoder模型名称
                - ms-marco-TinyBERT-L-2-v2: 2层，速度快6x (推荐)
                - ms-marco-TinyBERT-L-4: 4层，平衡版本
                - ms-marco-TinyBERT-L-6: 6层，准确率更高
        """
        print(f"[INFO] Loading Optimized Cross-Encoder: {model_name}")
        start_time = time.time()
        self.reranker = CrossEncoder(model_name)
        load_time = time.time() - start_time
        print(f"[OK] Reranker loaded in {load_time:.2f}s")

    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 5,
        batch_size: int = 32
    ) -> List[Dict]:
        """
        批量重排序文档 (优化版)

        Args:
            query: 用户查询
            documents: 初始检索结果
            top_k: 返回前K个结果
            batch_size: 批处理大小

        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []

        # 准备输入对
        pairs = [(query, doc['text']) for doc in documents]

        # 批量计算相关性分数 (优化点)
        scores = self.reranker.predict(
            pairs,
            batch_size=batch_size,
            show_progress_bar=False
        )

        # 添加分数到文档
        for doc, score in zip(documents, scores):
            doc['rerank_score'] = float(score)

        # 按分数排序
        reranked = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)

        return reranked[:top_k]


class OptimizedHybridRetriever:
    """优化版混合检索器: Qdrant + TinyBERT"""

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "sales_knowledge",
        reranker_model: str = "cross-encoder/ms-marco-TinyBERT-L-2-v2"
    ):
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.reranker = OptimizedNeuralReranker(reranker_model)

        # 创建session
        self.session = requests.Session()
        self.session.trust_env = False

    def search(
        self,
        query: str,
        query_vector: List[float],
        initial_k: int = 15,  # 优化: 50 → 15
        final_k: int = 5
    ) -> Dict:
        """
        优化版混合检索: 向量检索 + 快速重排序

        Args:
            query: 查询文本
            query_vector: 查询向量
            initial_k: 初始检索数量 (优化为15)
            final_k: 最终返回数量

        Returns:
            检索结果和性能指标
        """
        start_time = time.time()

        # Step 1: 向量检索 (快速但粗糙)
        vector_start = time.time()
        initial_results = self._vector_search(query_vector, initial_k)
        vector_time = time.time() - vector_start

        if not initial_results:
            return {
                "results": [],
                "metrics": {
                    "total_time_ms": (time.time() - start_time) * 1000,
                    "vector_time_ms": vector_time * 1000,
                    "rerank_time_ms": 0,
                    "initial_count": 0,
                    "final_count": 0
                }
            }

        # Step 2: 快速重排序 (TinyBERT)
        rerank_start = time.time()
        final_results = self.reranker.rerank(query, initial_results, final_k)
        rerank_time = time.time() - rerank_start

        total_time = time.time() - start_time

        return {
            "results": final_results,
            "metrics": {
                "total_time_ms": total_time * 1000,
                "vector_time_ms": vector_time * 1000,
                "rerank_time_ms": rerank_time * 1000,
                "initial_count": len(initial_results),
                "final_count": len(final_results)
            }
        }

    def _vector_search(self, query_vector: List[float], limit: int) -> List[Dict]:
        """向量检索"""
        search_payload = {
            "vector": {
                "name": "text",
                "vector": query_vector
            },
            "limit": limit,
            "with_payload": True
        }

        try:
            response = self.session.post(
                f"{self.qdrant_url}/collections/{self.collection_name}/points/search",
                json=search_payload,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("result", []):
                    results.append({
                        "id": item.get("id"),
                        "text": item.get("payload", {}).get("text", ""),
                        "source": item.get("payload", {}).get("source", ""),
                        "metadata": item.get("payload", {}).get("metadata", {}),
                        "vector_score": item.get("score", 0)
                    })
                return results
            else:
                print(f"[ERROR] Vector search failed: {response.status_code}")
                return []

        except Exception as e:
            print(f"[ERROR] Vector search exception: {str(e)}")
            return []


def benchmark_comparison():
    """性能对比测试: 原版 vs 优化版"""
    from sentence_transformers import SentenceTransformer

    print("\n" + "="*70)
    print("Week 1.5 Optimization Benchmark")
    print("="*70)

    # 加载embedding模型
    print("\n[INFO] Loading BGE-M3 for query encoding...")
    embedding_model = SentenceTransformer('BAAI/bge-m3')

    # 初始化两个版本
    print("\n[INFO] Initializing Original Retriever (MiniLM-L-12)...")
    from phase3a_day1_reranking import HybridRetriever as OriginalRetriever
    original_retriever = OriginalRetriever(
        reranker_model="cross-encoder/ms-marco-MiniLM-L-12-v2"
    )

    print("\n[INFO] Initializing Optimized Retriever (TinyBERT-L-2)...")
    optimized_retriever = OptimizedHybridRetriever()

    # 测试查询
    test_queries = [
        "信用卡有哪些权益？",
        "百夫长卡的高尔夫权益",
        "如何申请留学生卡？"
    ]

    results_comparison = []

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"Test Query {i}: {query}")
        print('='*70)

        # 生成查询向量
        query_vector = embedding_model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False
        )[0].tolist()

        # 原版检索
        print("\n[ORIGINAL] MiniLM-L-12 + 50 candidates")
        original_result = original_retriever.search(
            query=query,
            query_vector=query_vector,
            initial_k=50,
            final_k=5
        )
        original_metrics = original_result['metrics']
        print(f"  Total Time: {original_metrics['total_time_ms']:.1f}ms")
        print(f"  - Vector: {original_metrics['vector_time_ms']:.1f}ms")
        print(f"  - Rerank: {original_metrics['rerank_time_ms']:.1f}ms")
        print(f"  Top Score: {original_result['results'][0]['rerank_score']:.4f}")

        # 优化版检索
        print("\n[OPTIMIZED] TinyBERT-L-2 + 15 candidates")
        optimized_result = optimized_retriever.search(
            query=query,
            query_vector=query_vector,
            initial_k=15,
            final_k=5
        )
        optimized_metrics = optimized_result['metrics']
        print(f"  Total Time: {optimized_metrics['total_time_ms']:.1f}ms")
        print(f"  - Vector: {optimized_metrics['vector_time_ms']:.1f}ms")
        print(f"  - Rerank: {optimized_metrics['rerank_time_ms']:.1f}ms")
        print(f"  Top Score: {optimized_result['results'][0]['rerank_score']:.4f}")

        # 计算提升
        speedup = original_metrics['rerank_time_ms'] / optimized_metrics['rerank_time_ms']
        score_diff = optimized_result['results'][0]['rerank_score'] - original_result['results'][0]['rerank_score']

        print("\n[IMPROVEMENT]")
        print(f"  Speed: {speedup:.1f}x faster")
        print(f"  Score Diff: {score_diff:+.4f}")

        results_comparison.append({
            "query": query,
            "original_time": original_metrics['rerank_time_ms'],
            "optimized_time": optimized_metrics['rerank_time_ms'],
            "speedup": speedup,
            "original_score": original_result['results'][0]['rerank_score'],
            "optimized_score": optimized_result['results'][0]['rerank_score'],
            "score_diff": score_diff
        })

    # 总结
    print("\n" + "="*70)
    print("Benchmark Summary")
    print("="*70)

    avg_speedup = sum(r['speedup'] for r in results_comparison) / len(results_comparison)
    avg_score_diff = sum(r['score_diff'] for r in results_comparison) / len(results_comparison)

    print(f"\nAverage Speedup: {avg_speedup:.1f}x")
    print(f"Average Score Difference: {avg_score_diff:+.4f}")

    print("\n[SUCCESS] Week 1.5 Optimization Complete!")
    print("[INFO] Key improvements:")
    print(f"  - Reranking speed: {avg_speedup:.1f}x faster")
    print(f"  - Accuracy: {'Maintained' if abs(avg_score_diff) < 0.5 else 'Slightly changed'}")
    print("  - Candidates: 50 → 15 (70% reduction)")
    print("  - Model: 12 layers → 2 layers (6x smaller)")


def test_optimized_reranking():
    """快速测试优化版重排序"""
    from sentence_transformers import SentenceTransformer

    print("\n" + "="*70)
    print("Testing Optimized Cross-Encoder Reranking")
    print("="*70)

    # 加载embedding模型
    print("\n[INFO] Loading BGE-M3...")
    embedding_model = SentenceTransformer('BAAI/bge-m3')

    # 初始化优化版检索器
    print("[INFO] Initializing Optimized Retriever...")
    retriever = OptimizedHybridRetriever()

    # 测试查询
    test_queries = [
        "信用卡有哪些权益？",
        "百夫长卡的高尔夫权益",
        "如何申请留学生卡？"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"Test Query {i}: {query}")
        print('='*70)

        # 生成查询向量
        query_vector = embedding_model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False
        )[0].tolist()

        # 优化版检索
        result = retriever.search(
            query=query,
            query_vector=query_vector,
            initial_k=15,
            final_k=5
        )

        # 显示结果
        print("\n[METRICS]")
        metrics = result['metrics']
        print(f"  Total Time: {metrics['total_time_ms']:.1f}ms")
        print(f"  - Vector Search: {metrics['vector_time_ms']:.1f}ms")
        print(f"  - Reranking: {metrics['rerank_time_ms']:.1f}ms")
        print(f"  Initial Results: {metrics['initial_count']}")
        print(f"  Final Results: {metrics['final_count']}")

        print("\n[RESULTS]")
        for j, doc in enumerate(result['results'], 1):
            print(f"\n  Result {j}:")
            print(f"    Vector Score: {doc['vector_score']:.4f}")
            print(f"    Rerank Score: {doc['rerank_score']:.4f}")
            print(f"    Source: {doc['source']}")
            print(f"    Text: {doc['text'][:100]}...")

    print("\n" + "="*70)
    print("Optimized Reranking Test Complete")
    print("="*70)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--benchmark":
        benchmark_comparison()
    else:
        test_optimized_reranking()
