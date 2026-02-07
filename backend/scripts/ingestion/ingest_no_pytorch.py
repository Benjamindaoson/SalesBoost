#!/usr/bin/env python3
"""
Qdrant Ingestion - No PyTorch Version
使用 Qdrant REST API 和远程嵌入服务

不依赖本地 PyTorch，避免 Windows DLL 问题
"""

import json
import requests
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm


def load_chunks(file_path: Path) -> List[Dict]:
    """加载知识块"""
    print(f"[INFO] Loading chunks from: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    print(f"[OK] Loaded {len(chunks)} chunks")
    return chunks


def create_collection(qdrant_url: str, collection_name: str):
    """创建 Qdrant 集合"""
    print(f"\n[INFO] Creating collection: {collection_name}")

    # 创建 session 并禁用代理（避免 localhost 代理问题）
    session = requests.Session()
    session.trust_env = False  # 禁用环境变量中的代理设置

    # 检查集合是否存在
    response = session.get(f"{qdrant_url}/collections/{collection_name}")

    if response.status_code == 200:
        print("[INFO] Collection already exists")
        return True

    # 创建集合（使用命名向量）
    payload = {
        "vectors": {
            "text": {
                "size": 1024,  # BGE-M3 dimension
                "distance": "Cosine"
            }
        }
    }

    response = session.put(
        f"{qdrant_url}/collections/{collection_name}",
        json=payload
    )

    if response.status_code in [200, 201]:
        print("[OK] Collection created")
        return True
    else:
        print(f"[ERROR] Failed to create collection: {response.text}")
        return False


def generate_embeddings_api(texts: List[str], api_key: str) -> List[List[float]]:
    """使用 API 生成嵌入向量（避免本地 PyTorch）"""
    # 这里可以使用多种 API：
    # 1. OpenAI Embeddings API
    # 2. Cohere Embeddings API
    # 3. HuggingFace Inference API
    # 4. 自建的嵌入服务

    # 示例：使用 OpenAI API（如果有 key）
    try:
        from openai import OpenAI
        import os
        from dotenv import load_dotenv
        load_dotenv()

        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("[WARN] OPENAI_API_KEY not found, using mock embeddings")
            return generate_mock_embeddings(len(texts))

        client = OpenAI(api_key=openai_key)

        embeddings = []
        for text in tqdm(texts, desc="Generating embeddings"):
            response = client.embeddings.create(
                model="text-embedding-3-large",  # 3072 dimensions
                input=text[:8000]  # Truncate to avoid token limit
            )
            embeddings.append(response.data[0].embedding)

        return embeddings

    except Exception as e:
        print(f"[WARN] API embedding failed: {e}, using mock embeddings")
        return generate_mock_embeddings(len(texts))


def generate_mock_embeddings(count: int, dim: int = 1024) -> List[List[float]]:
    """生成模拟嵌入向量（用于测试）"""
    import random
    print(f"[WARN] Generating {count} mock embeddings (dimension={dim})")
    print("[WARN] These are random vectors and will NOT work for semantic search!")
    print("[WARN] This is only for testing the ingestion pipeline.")

    embeddings = []
    for _ in range(count):
        # 生成随机向量并归一化
        vector = [random.gauss(0, 1) for _ in range(dim)]
        norm = sum(x**2 for x in vector) ** 0.5
        vector = [x / norm for x in vector]
        embeddings.append(vector)

    return embeddings


def ingest_chunks_rest_api(
    chunks: List[Dict],
    qdrant_url: str = "http://localhost:6333",
    collection_name: str = "sales_knowledge",
    use_api_embeddings: bool = False
):
    """使用 REST API 导入数据"""
    print("\n" + "="*70)
    print("Ingesting to Qdrant via REST API")
    print("="*70)

    # 创建 session 并禁用代理
    session = requests.Session()
    session.trust_env = False  # 禁用环境变量中的代理设置

    # 创建集合
    if not create_collection(qdrant_url, collection_name):
        return False

    # 生成嵌入向量
    texts = [chunk["text"] for chunk in chunks]

    if use_api_embeddings:
        print("\n[INFO] Generating embeddings via API...")
        embeddings = generate_embeddings_api(texts, None)
    else:
        print("\n[INFO] Generating mock embeddings...")
        embeddings = generate_mock_embeddings(len(texts))

    # 批量上传
    batch_size = 32
    total_ingested = 0

    for i in tqdm(range(0, len(chunks), batch_size), desc="Uploading batches"):
        batch_chunks = chunks[i:i+batch_size]
        batch_embeddings = embeddings[i:i+batch_size]

        # 准备点
        points = []
        for j, chunk in enumerate(batch_chunks):
            point = {
                "id": hash(chunk["id"]) % (10 ** 8),  # 简单的 ID 转换
                "vector": {
                    "text": batch_embeddings[j]
                },
                "payload": {
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "type": chunk["type"],
                    "metadata": chunk["metadata"]
                }
            }
            points.append(point)

        # 上传
        response = session.put(
            f"{qdrant_url}/collections/{collection_name}/points",
            json={"points": points}
        )

        if response.status_code in [200, 201]:
            total_ingested += len(batch_chunks)
        else:
            print(f"\n[ERROR] Batch upload failed: {response.text}")

    print(f"\n[SUCCESS] Ingested {total_ingested}/{len(chunks)} chunks")

    # 验证
    response = session.get(f"{qdrant_url}/collections/{collection_name}")
    if response.status_code == 200:
        info = response.json()["result"]
        print("\n[INFO] Collection info:")
        print(f"  - Name: {info['name']}")
        print(f"  - Vectors count: {info.get('vectors_count', 'N/A')}")
        print(f"  - Points count: {info.get('points_count', 'N/A')}")

    return True


def main():
    """主函数"""
    print("\n" + "="*70)
    print("Qdrant Ingestion - No PyTorch Version")
    print("="*70)

    # 加载数据
    chunks_file = Path("storage/integrated_data/product_rights_chunks.json")

    if not chunks_file.exists():
        print(f"\n[ERROR] Chunks file not found: {chunks_file}")
        return

    chunks = load_chunks(chunks_file)

    # 导入
    print("\n[INFO] This script uses REST API and avoids PyTorch DLL issues")
    print("[WARN] Using mock embeddings (random vectors)")
    print("[WARN] For production, you need real embeddings from:")
    print("  1. OpenAI Embeddings API")
    print("  2. Cohere Embeddings API")
    print("  3. HuggingFace Inference API")
    print("  4. Self-hosted embedding service (on Linux)")

    success = ingest_chunks_rest_api(
        chunks,
        qdrant_url="http://localhost:6333",
        collection_name="sales_knowledge",
        use_api_embeddings=False  # Set to True if you have OpenAI API key
    )

    if success:
        print("\n" + "="*70)
        print("Ingestion Complete")
        print("="*70)
        print("\n[OK] Data ingested into Qdrant")
        print("[WARN] Using mock embeddings - semantic search will NOT work")
        print("[INFO] To fix: Generate real embeddings on Linux or via API")
    else:
        print("\n[FAILED] Ingestion failed")


if __name__ == "__main__":
    main()
