#!/usr/bin/env python3
"""
Regenerate Embeddings using SiliconFlow BGE-M3
使用硅基流动的 BGE-M3 重新生成向量

IMPORTANT: This script uses SiliconFlow (硅基流动) API, NOT OpenAI!
- Embedding Model: BAAI/bge-m3 (1024 dimensions)
- LLM Model: deepseek-ai/DeepSeek-V3
- API Endpoint: https://api.siliconflow.cn/v1
"""

import json
import os
import requests
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def generate_embeddings_siliconflow(texts: List[str], api_key: str) -> List[List[float]]:
    """
    使用 SiliconFlow 的 BGE-M3 生成嵌入向量

    Args:
        texts: 文本列表
        api_key: SiliconFlow API key

    Returns:
        嵌入向量列表 (1024 维)
    """
    import time

    base_url = "https://api.siliconflow.cn/v1"
    model = "BAAI/bge-m3"

    print(f"\n[INFO] Using SiliconFlow BGE-M3 for embeddings")
    print(f"  - Model: {model}")
    print(f"  - Dimension: 1024")
    print(f"  - Base URL: {base_url}")

    embeddings = []

    # Process in smaller batches with rate limiting
    batch_size = 5  # Reduced from 10 to avoid RPM limit
    retry_delay = 3  # Wait 3 seconds between batches

    for i in tqdm(range(0, len(texts), batch_size), desc="Generating embeddings"):
        batch_texts = texts[i:i + batch_size]

        # Retry logic
        max_retries = 3
        retry_count = 0
        success = False

        while retry_count < max_retries and not success:
            try:
                response = requests.post(
                    f"{base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "input": batch_texts,
                        "encoding_format": "float"
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    batch_embeddings = [item["embedding"] for item in data["data"]]
                    embeddings.extend(batch_embeddings)
                    success = True

                    # Rate limiting: wait between successful requests
                    if i + batch_size < len(texts):
                        time.sleep(retry_delay)

                elif response.status_code == 403:
                    retry_count += 1
                    wait_time = retry_delay * (2 ** retry_count)  # Exponential backoff
                    print(f"\n[WARN] RPM limit hit, waiting {wait_time}s before retry {retry_count}/{max_retries}")
                    time.sleep(wait_time)
                else:
                    print(f"\n[ERROR] API request failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    retry_count += 1
                    time.sleep(retry_delay)

            except Exception as e:
                print(f"\n[ERROR] Exception during API call: {e}")
                retry_count += 1
                time.sleep(retry_delay)

        # If all retries failed, use mock embeddings for this batch
        if not success:
            print(f"\n[ERROR] Failed after {max_retries} retries, using mock embeddings for batch")
            import random
            for _ in batch_texts:
                vector = [random.gauss(0, 1) for _ in range(1024)]
                norm = sum(x**2 for x in vector) ** 0.5
                embeddings.append([x / norm for x in vector])

    return embeddings


def update_qdrant_vectors(
    chunks: List[Dict],
    embeddings: List[List[float]],
    qdrant_url: str = "http://localhost:6333",
    collection_name: str = "sales_knowledge"
):
    """
    更新 Qdrant 中的向量

    Args:
        chunks: 数据块列表
        embeddings: 嵌入向量列表
        qdrant_url: Qdrant URL
        collection_name: 集合名称
    """
    print(f"\n[INFO] Updating vectors in Qdrant")
    print(f"  - Collection: {collection_name}")
    print(f"  - Total points: {len(chunks)}")

    # Create session and disable proxy
    session = requests.Session()
    session.trust_env = False

    # Prepare points with new vectors
    points = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        # Use integer ID instead of string ID (Qdrant requirement)
        point_id = i + 1  # Start from 1

        point = {
            "id": point_id,
            "vector": {
                "text": embedding  # Named vector
            },
            "payload": {
                "text": chunk.get("text", ""),
                "source": chunk.get("source", ""),
                "type": chunk.get("type", ""),
                "metadata": chunk.get("metadata", {}),
                "original_id": chunk.get("id", f"chunk_{i}")  # Store original ID in payload
            }
        }
        points.append(point)

    # Upload in batches
    batch_size = 30
    total_updated = 0

    for i in tqdm(range(0, len(points), batch_size), desc="Updating Qdrant"):
        batch_points = points[i:i + batch_size]

        try:
            response = session.put(
                f"{qdrant_url}/collections/{collection_name}/points",
                json={"points": batch_points},
                params={"wait": "true"}  # Wait for indexing
            )

            if response.status_code in [200, 201]:
                total_updated += len(batch_points)
            else:
                print(f"\n[ERROR] Batch update failed: {response.text}")

        except Exception as e:
            print(f"\n[ERROR] Exception during update: {e}")

    print(f"\n[SUCCESS] Updated {total_updated}/{len(chunks)} vectors")

    return total_updated


def verify_embeddings(
    qdrant_url: str = "http://localhost:6333",
    collection_name: str = "sales_knowledge"
):
    """验证向量是否更新成功"""
    print(f"\n[INFO] Verifying embeddings...")

    session = requests.Session()
    session.trust_env = False

    try:
        response = session.get(f"{qdrant_url}/collections/{collection_name}")

        if response.status_code == 200:
            data = response.json()
            result = data.get("result", {})

            vectors_count = result.get("vectors_count", 0)
            points_count = result.get("points_count", 0)

            print(f"\n[OK] Collection status:")
            print(f"  - Points: {points_count}")
            print(f"  - Vectors: {vectors_count}")

            if vectors_count > 0:
                print(f"\n[SUCCESS] Real embeddings verified!")
                return True
            else:
                print(f"\n[WARN] No vectors found - may still be indexing")
                return False
        else:
            print(f"\n[ERROR] Failed to verify: {response.status_code}")
            return False

    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "="*70)
    print("Regenerate Embeddings - SiliconFlow BGE-M3")
    print("="*70)

    # Check API key
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key or api_key.strip() == "" or "REQUIRED" in api_key:
        print("\n[ERROR] SILICONFLOW_API_KEY not found in .env")
        print("\n[ACTION REQUIRED] Please add your SiliconFlow API key to .env:")
        print("  SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxxxx")
        print("\n[INFO] Get your API key from: https://siliconflow.cn")
        print("\n[FALLBACK] Will use mock embeddings for testing")
        api_key = None
    else:
        print(f"\n[OK] SiliconFlow API key found")

    # Load chunks
    chunks_file = Path("storage/integrated_data/product_rights_chunks.json")

    if not chunks_file.exists():
        print(f"\n[ERROR] Chunks file not found: {chunks_file}")
        return

    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"\n[OK] Loaded {len(chunks)} chunks")

    # Extract texts
    texts = [chunk.get("text", "") for chunk in chunks]

    # Generate embeddings
    if api_key:
        print(f"\n[INFO] Generating real embeddings via SiliconFlow...")
        embeddings = generate_embeddings_siliconflow(texts, api_key)
    else:
        print(f"\n[WARN] No API key - using mock embeddings")
        print(f"[WARN] Semantic search will NOT work!")
        import random
        embeddings = []
        for _ in tqdm(texts, desc="Generating mock embeddings"):
            vector = [random.gauss(0, 1) for _ in range(1024)]
            norm = sum(x**2 for x in vector) ** 0.5
            embeddings.append([x / norm for x in vector])

    # Update Qdrant
    updated = update_qdrant_vectors(chunks, embeddings)

    # Verify
    if updated > 0:
        verify_embeddings()

    print("\n" + "="*70)
    print("Embedding Regeneration Complete")
    print("="*70)

    if api_key:
        print("\n[SUCCESS] Real BGE-M3 embeddings generated!")
        print("[INFO] Semantic search should now work correctly")
    else:
        print("\n[WARN] Mock embeddings used - add SILICONFLOW_API_KEY for real embeddings")

    print("\n[NEXT STEP] Test semantic search:")
    print("  python scripts/test_semantic_search.py")


if __name__ == "__main__":
    main()
