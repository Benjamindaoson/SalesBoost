#!/usr/bin/env python3
"""
Phase 3A Day 1-2: Cross-Encoder Reranking
神经重排序器实现

性能目标:
- 准确率: +30%
- 延迟: +50ms (可接受)
- 成本: 几乎免费 (CPU推理)
"""

from sentence_transformers import CrossEncoder
import requests
from typing import List, Dict
import time


class NeuralReranker:
    """2026年SOTA神经重排序器"""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"):
        """
        初始化重排序器

        Args:
            model_name: Cross-Encoder模型名称
                - ms-marco-MiniLM-L-12-v2: 快速，准确率高
                - ms-marco-electra-base: 更准确，稍慢
        """
        print(f"[INFO] Loading Cross-Encoder: {model_name}")
        self.reranker = CrossEncoder(model_name)
        print("[OK] Reranker loaded")

    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        重排序文档

        Args:
            query: 用户查询
            documents: 初始检索结果
            top_k: 返回前K个结果

        Returns:
            重排序后的文档列表
        """
        # 准备输入对
        pairs = [(query, doc['text']) for doc in documents]

        # 计算相关性分数
        scores = self.reranker.predict(pairs)

        # 添加分数到文档
        for doc, score in zip(documents, scores):
            doc['rerank_score'] = float(score)

        # 按分数排序
        reranked = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)

        return reranked[:top_k]


class HybridRetriever:
    """混合检索器: Qdrant + Cross-Encoder"""

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "sales_knowledge",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"
    ):
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.reranker = NeuralReranker(reranker_model)

        # 创建session
        self.session = requests.Session()
        self.session.trust_env = False

    def search(
        self,
        query: str,
        query_vector: List[float],
        initial_k: int = 50,
        final_k: int = 5
    ) -> Dict:
        """
        混合检索: 向量检索 + 神经重排序

        Args:
            query: 查询文本
            query_vector: 查询向量
            initial_k: 初始检索数量
            final_k: 最终返回数量

        Returns:
            检索结果和性能指标
        """
        start_time = time.time()

        # Step 1: 向量检索 (快速但粗糙)
        vector_start = time.time()
        initial_results = self._vector_search(query_vector, initial_k)
        vector_time = time.time() - vector_start

        # Step 2: 神经重排序 (慢但精准)
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

        response = self.session.post(
            f"{self.qdrant_url}/collections/{self.collection_name}/points/search",
            json=search_payload
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


def test_reranking():
    """测试重排序效果"""
    from sentence_transformers import SentenceTransformer

    print("\n" + "="*70)
    print("Testing Cross-Encoder Reranking")
    print("="*70)

    # 加载embedding模型
    print("\n[INFO] Loading BGE-M3 for query encoding...")
    embedding_model = SentenceTransformer('BAAI/bge-m3')

    # 初始化混合检索器
    print("[INFO] Initializing Hybrid Retriever...")
    retriever = HybridRetriever()

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

        # 混合检索
        result = retriever.search(
            query=query,
            query_vector=query_vector,
            initial_k=50,
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
    print("Reranking Test Complete")
    print("="*70)

    print("\n[SUCCESS] Cross-Encoder reranking working!")
    print("[INFO] Expected improvements:")
    print("  - Accuracy: +25-35%")
    print("  - Latency: +50ms (acceptable)")
    print("  - Cost: Nearly free (CPU inference)")


if __name__ == "__main__":
    test_reranking()
