#!/usr/bin/env python3
"""
Test Semantic Search with LOCAL BGE-M3
测试语义搜索 (使用本地 BGE-M3)

This script tests semantic search quality using local BGE-M3 for query embeddings.
"""

import requests
from sentence_transformers import SentenceTransformer


def generate_query_embedding_local(query_text: str, model) -> list:
    """
    使用本地 BGE-M3 生成查询向量

    Args:
        query_text: 查询文本
        model: SentenceTransformer model

    Returns:
        查询向量 (1024 维)
    """
    embedding = model.encode(
        [query_text],
        normalize_embeddings=True,
        show_progress_bar=False
    )
    return embedding[0].tolist()


def search_qdrant(
    query_vector: list,
    qdrant_url: str = "http://localhost:6333",
    collection_name: str = "sales_knowledge",
    limit: int = 3
):
    """
    在 Qdrant 中搜索

    Args:
        query_vector: 查询向量
        qdrant_url: Qdrant URL
        collection_name: 集合名称
        limit: 返回结果数量

    Returns:
        搜索结果
    """
    session = requests.Session()
    session.trust_env = False

    search_payload = {
        "vector": {
            "name": "text",
            "vector": query_vector
        },
        "limit": limit,
        "with_payload": True
    }

    try:
        response = session.post(
            f"{qdrant_url}/collections/{collection_name}/points/search",
            json=search_payload
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("result", [])
        else:
            print(f"[ERROR] Search failed: {response.status_code}")
            print(f"Response: {response.text}")
            return []

    except Exception as e:
        print(f"[ERROR] Search exception: {e}")
        return []


def test_semantic_search():
    """测试语义搜索"""
    print("\n" + "="*70)
    print("Testing Semantic Search - LOCAL BGE-M3")
    print("="*70)

    print("\n[INFO] Loading BGE-M3 model locally...")
    model = SentenceTransformer('BAAI/bge-m3')
    print("[OK] Model loaded")

    # Test queries
    test_queries = [
        {
            "query": "信用卡有哪些权益？",
            "expected": "product_rights"
        },
        {
            "query": "百夫长卡的高尔夫权益",
            "expected": "golf, centurion"
        },
        {
            "query": "如何申请留学生卡？",
            "expected": "student, application"
        },
        {
            "query": "机场贵宾厅服务",
            "expected": "lounge, airport"
        }
    ]

    for i, test_case in enumerate(test_queries, 1):
        query_text = test_case["query"]
        expected = test_case["expected"]

        print(f"\n{'='*70}")
        print(f"Test Query {i}: {query_text}")
        print(f"Expected keywords: {expected}")
        print('='*70)

        # Generate query embedding
        print("\n[INFO] Generating query embedding locally...")
        query_vector = generate_query_embedding_local(query_text, model)
        print(f"[OK] Query vector generated (dimension: {len(query_vector)})")

        # Search
        print("\n[INFO] Searching Qdrant...")
        results = search_qdrant(query_vector)

        if not results:
            print("[ERROR] No results found")
            continue

        print(f"\n[OK] Found {len(results)} results")

        # Display results
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

            # Check if result is relevant
            if score > 0.5:
                print("    [OK] High relevance score")
            elif score > 0.3:
                print("    [WARN] Medium relevance score")
            else:
                print("    [ERROR] Low relevance score")

    print("\n" + "="*70)
    print("Semantic Search Test Complete")
    print("="*70)

    print("\n[INFO] Interpretation:")
    print("  - Score > 0.7: Highly relevant")
    print("  - Score 0.5-0.7: Relevant")
    print("  - Score 0.3-0.5: Somewhat relevant")
    print("  - Score < 0.3: Not relevant")

    print("\n[SUCCESS] 100% Local processing - No API calls!")


if __name__ == "__main__":
    test_semantic_search()
