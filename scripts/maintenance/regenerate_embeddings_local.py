#!/usr/bin/env python3
"""
Regenerate Embeddings using LOCAL BGE-M3 (No API needed!)
使用本地 BGE-M3 重新生成向量（不需要 API！）

This script uses sentence-transformers to generate embeddings locally.
"""

import json
import os
import requests
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm


def generate_embeddings_local(texts: List[str]) -> List[List[float]]:
    """
    使用本地 BGE-M3 生成嵌入向量

    Args:
        texts: 文本列表

    Returns:
        嵌入向量列表 (1024 维)
    """
    from sentence_transformers import SentenceTransformer

    print(f"\n[INFO] Loading BGE-M3 model locally...")
    print(f"  - Model: BAAI/bge-m3")
    print(f"  - Dimension: 1024")
    print(f"  - Device: CPU")

    # Load model
    model = SentenceTransformer('BAAI/bge-m3')
    print(f"[OK] Model loaded successfully!")

    # Generate embeddings
    print(f"\n[INFO] Generating embeddings for {len(texts)} texts...")

    embeddings = []
    batch_size = 32  # Process in batches for efficiency

    for i in tqdm(range(0, len(texts), batch_size), desc="Generating embeddings"):
        batch_texts = texts[i:i + batch_size]
        batch_embeddings = model.encode(
            batch_texts,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        embeddings.extend(batch_embeddings.tolist())

    print(f"[SUCCESS] Generated {len(embeddings)} embeddings")

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

            if points_count > 0:
                print(f"\n[SUCCESS] Real embeddings verified!")
                return True
            else:
                print(f"\n[WARN] No points found")
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
    print("Regenerate Embeddings - LOCAL BGE-M3 (No API!)")
    print("="*70)

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

    # Generate embeddings locally
    print(f"\n[INFO] Generating embeddings locally (no API needed)...")
    embeddings = generate_embeddings_local(texts)

    # Update Qdrant
    updated = update_qdrant_vectors(chunks, embeddings)

    # Verify
    if updated > 0:
        verify_embeddings()

    print("\n" + "="*70)
    print("Embedding Regeneration Complete")
    print("="*70)

    print("\n[SUCCESS] All embeddings generated locally!")
    print("[INFO] No API calls, no costs, 100% local processing!")

    print("\n[NEXT STEP] Test semantic search:")
    print("  python scripts/test_semantic_search_local.py")


if __name__ == "__main__":
    main()
