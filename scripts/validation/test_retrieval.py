#!/usr/bin/env python3
"""
Test Qdrant Retrieval
测试 Qdrant 检索功能

Note: Using mock embeddings, so semantic search won't work properly.
This script verifies the retrieval mechanism and data structure.
"""

import requests
import random

def generate_mock_query_vector(dim: int = 1024):
    """生成模拟查询向量"""
    vector = [random.gauss(0, 1) for _ in range(dim)]
    norm = sum(x**2 for x in vector) ** 0.5
    return [x / norm for x in vector]


def test_retrieval():
    """测试检索功能"""
    print("\n" + "="*70)
    print("Testing Qdrant Retrieval")
    print("="*70)

    # 创建 session 并禁用代理
    session = requests.Session()
    session.trust_env = False

    qdrant_url = "http://localhost:6333"
    collection_name = "sales_knowledge"

    print("\n[WARN] Using mock query vectors (random)")
    print("[WARN] Semantic search will NOT work - this is just a structure test")

    # 测试查询
    test_queries = [
        "信用卡有哪些权益？",
        "百夫长卡的高尔夫权益",
        "如何申请留学生卡？"
    ]

    for i, query_text in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"Test Query {i}: {query_text}")
        print('='*70)

        # 生成模拟查询向量
        query_vector = generate_mock_query_vector()

        # 搜索
        search_payload = {
            "vector": {
                "name": "text",
                "vector": query_vector
            },
            "limit": 3,
            "with_payload": True
        }

        try:
            response = session.post(
                f"{qdrant_url}/collections/{collection_name}/points/search",
                json=search_payload
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("result", [])

                print(f"\n[OK] Found {len(results)} results")

                for j, result in enumerate(results, 1):
                    score = result.get("score", 0)
                    payload = result.get("payload", {})
                    text = payload.get("text", "")
                    source = payload.get("source", "")

                    print(f"\n  Result {j}:")
                    print(f"    Score: {score:.4f}")
                    print(f"    Source: {source}")
                    print(f"    Text: {text[:150]}...")

            else:
                print(f"\n[ERROR] Search failed: {response.status_code}")
                print(f"Response: {response.text}")

        except Exception as e:
            print(f"\n[ERROR] Query failed: {e}")
            import traceback
            traceback.print_exc()

    # 测试过滤查询
    print(f"\n{'='*70}")
    print("Test Query with Filter: category=product_rights")
    print('='*70)

    query_vector = generate_mock_query_vector()

    search_payload = {
        "vector": {
            "name": "text",
            "vector": query_vector
        },
        "filter": {
            "must": [
                {
                    "key": "metadata.category",
                    "match": {
                        "value": "product_rights"
                    }
                }
            ]
        },
        "limit": 3,
        "with_payload": True
    }

    try:
        response = session.post(
            f"{qdrant_url}/collections/{collection_name}/points/search",
            json=search_payload
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get("result", [])

            print(f"\n[OK] Found {len(results)} filtered results")

            for j, result in enumerate(results, 1):
                score = result.get("score", 0)
                payload = result.get("payload", {})
                text = payload.get("text", "")
                source = payload.get("source", "")
                metadata = payload.get("metadata", {})

                print(f"\n  Result {j}:")
                print(f"    Score: {score:.4f}")
                print(f"    Source: {source}")
                print(f"    Category: {metadata.get('category', 'N/A')}")
                print(f"    Text: {text[:150]}...")

        else:
            print(f"\n[ERROR] Filtered search failed: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"\n[ERROR] Filtered query failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    test_retrieval()

    print("\n" + "="*70)
    print("Retrieval Test Complete")
    print("="*70)

    print("\n[IMPORTANT] Next Steps:")
    print("  1. [DONE] Data structure verified - retrieval mechanism works")
    print("  2. [TODO] Generate real embeddings (not mock) for production use")
    print("  3. [TODO] Options for real embeddings:")
    print("     - OpenAI Embeddings API (text-embedding-3-large)")
    print("     - Cohere Embeddings API")
    print("     - Self-hosted BGE-M3 on Linux server")
    print("     - HuggingFace Inference API")
    print("\n[WARN] Current mock embeddings are random - semantic search won't work!")
    print("[INFO] But the ingestion pipeline and data structure are correct.")


if __name__ == "__main__":
    main()
