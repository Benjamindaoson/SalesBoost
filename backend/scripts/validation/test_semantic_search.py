#!/usr/bin/env python3
"""
Test Semantic Search with SiliconFlow BGE-M3
测试语义搜索 (使用硅基流动 BGE-M3)

This script tests semantic search quality using real embeddings.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def generate_query_embedding(query_text: str, api_key: str) -> list:
    """
    使用 SiliconFlow BGE-M3 生成查询向量

    Args:
        query_text: 查询文本
        api_key: SiliconFlow API key

    Returns:
        查询向量 (1024 维)
    """
    base_url = "https://api.siliconflow.cn/v1"
    model = "BAAI/bge-m3"

    try:
        response = requests.post(
            f"{base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "input": [query_text],
                "encoding_format": "float"
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            return data["data"][0]["embedding"]
        else:
            print(f"[ERROR] API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return None


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
    print("Testing Semantic Search - SiliconFlow BGE-M3")
    print("="*70)

    # Check API key
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key or api_key.strip() == "" or "REQUIRED" in api_key:
        print("\n[ERROR] SILICONFLOW_API_KEY not found in .env")
        print("\n[ACTION REQUIRED] Please add your SiliconFlow API key to .env:")
        print("  SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxxxx")
        print("\n[INFO] Get your API key from: https://siliconflow.cn")
        return

    print("\n[OK] SiliconFlow API key found")

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
        print("\n[INFO] Generating query embedding...")
        query_vector = generate_query_embedding(query_text, api_key)

        if not query_vector:
            print("[ERROR] Failed to generate query embedding")
            continue

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
            print(f"    Text: {text[:200]}...")

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

    print("\n[SUCCESS] If scores are > 0.5, semantic search is working!")


if __name__ == "__main__":
    test_semantic_search()
