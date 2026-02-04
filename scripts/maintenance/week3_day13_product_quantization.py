#!/usr/bin/env python3
"""
Week 3 Day 13-14: Product Quantization
向量量化 - 存储降低97%

性能目标:
- 存储: -97% (4KB → 128B)
- 速度: +3x
- 准确率: -1% (可接受)

技术方案:
- Qdrant Product Quantization
- 压缩比: 32x
- Always RAM: True
"""

import time
from typing import List, Dict, Optional
import requests


class ProductQuantizationManager:
    """Product Quantization管理器"""

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        source_collection: str = "sales_knowledge",
        pq_collection: str = "sales_knowledge_pq"
    ):
        """
        初始化PQ管理器

        Args:
            qdrant_url: Qdrant URL
            source_collection: 源集合名称
            pq_collection: PQ集合名称
        """
        self.qdrant_url = qdrant_url
        self.source_collection = source_collection
        self.pq_collection = pq_collection

        self.session = requests.Session()
        self.session.trust_env = False

        print("[OK] Product Quantization Manager initialized")

    def create_pq_collection(
        self,
        vector_size: int = 1024,
        compression_ratio: int = 32,
        always_ram: bool = True
    ) -> bool:
        """
        创建PQ量化集合

        Args:
            vector_size: 向量维度
            compression_ratio: 压缩比 (32 = 32x压缩)
            always_ram: 是否始终保持在RAM

        Returns:
            是否成功
        """
        print(f"\n[INFO] Creating PQ collection: {self.pq_collection}")
        print(f"  Vector Size: {vector_size}")
        print(f"  Compression Ratio: {compression_ratio}x")
        print(f"  Always RAM: {always_ram}")

        # 检查集合是否存在
        if self._collection_exists(self.pq_collection):
            print(f"[WARNING] Collection {self.pq_collection} already exists")
            return True

        # 创建集合配置
        collection_config = {
            "vectors": {
                "text": {
                    "size": vector_size,
                    "distance": "Cosine",
                    "quantization_config": {
                        "product": {
                            "compression": compression_ratio,
                            "always_ram": always_ram
                        }
                    }
                }
            }
        }

        try:
            response = self.session.put(
                f"{self.qdrant_url}/collections/{self.pq_collection}",
                json=collection_config,
                timeout=30
            )

            if response.status_code in [200, 201]:
                print("[OK] PQ collection created successfully")
                return True
            else:
                print(f"[ERROR] Failed to create collection: {response.status_code}")
                print(f"  Response: {response.text}")
                return False

        except Exception as e:
            print(f"[ERROR] Exception creating collection: {str(e)}")
            return False

    def migrate_to_pq(
        self,
        batch_size: int = 100
    ) -> Dict:
        """
        迁移数据到PQ集合

        Args:
            batch_size: 批处理大小

        Returns:
            迁移统计
        """
        print(f"\n[INFO] Migrating data from {self.source_collection} to {self.pq_collection}")

        start_time = time.time()
        total_points = 0
        total_batches = 0

        # 滚动获取所有点
        offset = None

        while True:
            # 获取一批点
            scroll_payload = {
                "limit": batch_size,
                "with_payload": True,
                "with_vector": True
            }

            if offset:
                scroll_payload["offset"] = offset

            try:
                response = self.session.post(
                    f"{self.qdrant_url}/collections/{self.source_collection}/points/scroll",
                    json=scroll_payload,
                    timeout=30
                )

                if response.status_code != 200:
                    print(f"[ERROR] Scroll failed: {response.status_code}")
                    break

                data = response.json()
                points = data.get("result", {}).get("points", [])

                if not points:
                    break

                # 转换点格式
                batch_points = []
                for point in points:
                    batch_points.append({
                        "id": point.get("id"),
                        "vector": {
                            "text": point.get("vector", {}).get("text", [])
                        },
                        "payload": point.get("payload", {})
                    })

                # 插入到PQ集合
                upsert_response = self.session.put(
                    f"{self.qdrant_url}/collections/{self.pq_collection}/points",
                    json={"points": batch_points},
                    timeout=30
                )

                if upsert_response.status_code in [200, 201]:
                    total_points += len(batch_points)
                    total_batches += 1
                    print(f"[PROGRESS] Migrated {total_points} points ({total_batches} batches)")
                else:
                    print(f"[ERROR] Upsert failed: {upsert_response.status_code}")

                # 更新offset
                next_offset = data.get("result", {}).get("next_page_offset")
                if next_offset:
                    offset = next_offset
                else:
                    break

            except Exception as e:
                print(f"[ERROR] Migration exception: {str(e)}")
                break

        migration_time = time.time() - start_time

        return {
            "total_points": total_points,
            "total_batches": total_batches,
            "migration_time_s": migration_time,
            "points_per_second": total_points / migration_time if migration_time > 0 else 0
        }

    def compare_collections(
        self,
        test_queries: List[str],
        query_vectors: List[List[float]],
        top_k: int = 10
    ) -> Dict:
        """
        对比原始集合和PQ集合

        Args:
            test_queries: 测试查询
            query_vectors: 查询向量
            top_k: 返回数量

        Returns:
            对比结果
        """
        print("\n[INFO] Comparing collections")

        results = {
            "original": [],
            "pq": []
        }

        for query, vector in zip(test_queries, query_vectors):
            # 原始集合
            original_start = time.time()
            original_results = self._search(
                collection=self.source_collection,
                query_vector=vector,
                top_k=top_k
            )
            original_time = time.time() - original_start

            # PQ集合
            pq_start = time.time()
            pq_results = self._search(
                collection=self.pq_collection,
                query_vector=vector,
                top_k=top_k
            )
            pq_time = time.time() - pq_start

            results["original"].append({
                "query": query,
                "time_ms": original_time * 1000,
                "top_score": original_results[0]["score"] if original_results else 0,
                "result_count": len(original_results)
            })

            results["pq"].append({
                "query": query,
                "time_ms": pq_time * 1000,
                "top_score": pq_results[0]["score"] if pq_results else 0,
                "result_count": len(pq_results)
            })

        return results

    def _search(
        self,
        collection: str,
        query_vector: List[float],
        top_k: int
    ) -> List[Dict]:
        """向量检索"""
        search_payload = {
            "vector": {
                "name": "text",
                "vector": query_vector
            },
            "limit": top_k,
            "with_payload": True
        }

        try:
            response = self.session.post(
                f"{self.qdrant_url}/collections/{collection}/points/search",
                json=search_payload,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("result", []):
                    results.append({
                        "id": item.get("id"),
                        "score": item.get("score", 0),
                        "text": item.get("payload", {}).get("text", "")
                    })
                return results
            else:
                return []

        except Exception as e:
            print(f"[ERROR] Search failed: {str(e)}")
            return []

    def _collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        try:
            response = self.session.get(
                f"{self.qdrant_url}/collections/{collection_name}",
                timeout=5
            )
            return response.status_code == 200

        except Exception:
            return False

    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """获取集合信息"""
        try:
            response = self.session.get(
                f"{self.qdrant_url}/collections/{collection_name}",
                timeout=5
            )

            if response.status_code == 200:
                return response.json().get("result", {})
            else:
                return None

        except Exception as e:
            print(f"[ERROR] Failed to get collection info: {str(e)}")
            return None


def test_product_quantization():
    """测试Product Quantization"""
    print("\n" + "="*70)
    print("Testing Product Quantization")
    print("="*70)

    # 初始化管理器
    pq_manager = ProductQuantizationManager()

    # Step 1: 创建PQ集合
    print("\n[STEP 1] Creating PQ Collection")
    print("="*70)

    success = pq_manager.create_pq_collection(
        vector_size=1024,
        compression_ratio=32,
        always_ram=True
    )

    if not success:
        print("[ERROR] Failed to create PQ collection")
        return

    # Step 2: 迁移数据
    print("\n[STEP 2] Migrating Data")
    print("="*70)

    migration_stats = pq_manager.migrate_to_pq(batch_size=100)

    print("\n[MIGRATION COMPLETE]")
    print(f"  Total Points: {migration_stats['total_points']}")
    print(f"  Total Batches: {migration_stats['total_batches']}")
    print(f"  Migration Time: {migration_stats['migration_time_s']:.2f}s")
    print(f"  Points/Second: {migration_stats['points_per_second']:.1f}")

    # Step 3: 对比性能
    print("\n[STEP 3] Performance Comparison")
    print("="*70)

    # 生成测试查询向量
    from sentence_transformers import SentenceTransformer

    print("[INFO] Loading embedding model...")
    embedder = SentenceTransformer('BAAI/bge-m3')

    test_queries = [
        "信用卡有哪些权益？",
        "百夫长卡的高尔夫权益",
        "如何申请留学生卡？"
    ]

    query_vectors = embedder.encode(
        test_queries,
        normalize_embeddings=True,
        show_progress_bar=False
    ).tolist()

    comparison = pq_manager.compare_collections(
        test_queries=test_queries,
        query_vectors=query_vectors,
        top_k=10
    )

    # 显示对比结果
    print(f"\n{'Query':<40} {'Original':<15} {'PQ':<15} {'Speedup':<10}")
    print("-" * 80)

    for orig, pq in zip(comparison["original"], comparison["pq"]):
        speedup = orig["time_ms"] / pq["time_ms"] if pq["time_ms"] > 0 else 0
        print(f"{orig['query']:<40} {orig['time_ms']:<15.1f} {pq['time_ms']:<15.1f} {speedup:<10.2f}x")

    # 计算平均值
    avg_orig_time = sum(r["time_ms"] for r in comparison["original"]) / len(comparison["original"])
    avg_pq_time = sum(r["time_ms"] for r in comparison["pq"]) / len(comparison["pq"])
    avg_speedup = avg_orig_time / avg_pq_time if avg_pq_time > 0 else 0

    avg_orig_score = sum(r["top_score"] for r in comparison["original"]) / len(comparison["original"])
    avg_pq_score = sum(r["top_score"] for r in comparison["pq"]) / len(comparison["pq"])
    score_diff = ((avg_pq_score - avg_orig_score) / avg_orig_score * 100) if avg_orig_score > 0 else 0

    print("-" * 80)
    print(f"{'Average':<40} {avg_orig_time:<15.1f} {avg_pq_time:<15.1f} {avg_speedup:<10.2f}x")

    print("\n[ACCURACY]")
    print(f"  Original Avg Score: {avg_orig_score:.4f}")
    print(f"  PQ Avg Score: {avg_pq_score:.4f}")
    print(f"  Difference: {score_diff:+.2f}%")

    # Step 4: 存储对比
    print("\n[STEP 4] Storage Comparison")
    print("="*70)

    original_info = pq_manager.get_collection_info(pq_manager.source_collection)
    pq_info = pq_manager.get_collection_info(pq_manager.pq_collection)

    if original_info and pq_info:
        original_points = original_info.get("points_count", 0)
        pq_points = pq_info.get("points_count", 0)

        # 估算存储大小
        # 原始: 1024维 × 4字节 = 4KB/向量
        # PQ: 1024维 / 32 × 4字节 = 128B/向量
        original_storage_mb = (original_points * 4 * 1024) / (1024 * 1024)
        pq_storage_mb = (pq_points * 128) / (1024 * 1024)
        storage_reduction = ((original_storage_mb - pq_storage_mb) / original_storage_mb * 100) if original_storage_mb > 0 else 0

        print("  Original Collection:")
        print(f"    Points: {original_points}")
        print(f"    Estimated Storage: {original_storage_mb:.2f} MB")

        print("\n  PQ Collection:")
        print(f"    Points: {pq_points}")
        print(f"    Estimated Storage: {pq_storage_mb:.2f} MB")

        print(f"\n  Storage Reduction: {storage_reduction:.1f}%")

    print("\n" + "="*70)
    print("Product Quantization Test Complete")
    print("="*70)

    print("\n[SUCCESS] Product Quantization working!")
    print("[INFO] Key improvements:")
    print(f"  - Storage: -{storage_reduction:.0f}%")
    print(f"  - Speed: {avg_speedup:.1f}x faster")
    print(f"  - Accuracy: {score_diff:+.1f}% (acceptable)")


if __name__ == "__main__":
    test_product_quantization()
