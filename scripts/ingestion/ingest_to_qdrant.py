#!/usr/bin/env python3
"""
Ingest Product Rights Chunks into Qdrant
将产品权益知识块导入 Qdrant

Usage:
    python scripts/ingest_to_qdrant.py
"""

import sys
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_chunks(file_path: Path) -> List[Dict]:
    """加载知识块"""
    print(f"[INFO] Loading chunks from: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    print(f"[OK] Loaded {len(chunks)} chunks")
    return chunks


def ingest_to_qdrant_simple(chunks: List[Dict]):
    """简单导入到 Qdrant（示例）"""
    print("\n" + "="*70)
    print("Ingesting to Qdrant")
    print("="*70)

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        from sentence_transformers import SentenceTransformer

        # 连接 Qdrant
        print("\n[INFO] Connecting to Qdrant...")
        client = QdrantClient(url="http://localhost:6333")

        # 检查集合是否存在
        collection_name = "sales_knowledge"
        collections = client.get_collections().collections
        collection_exists = any(c.name == collection_name for c in collections)

        if not collection_exists:
            print(f"[INFO] Creating collection: {collection_name}")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=1024,  # BGE-M3 dimension
                    distance=Distance.COSINE
                )
            )
        else:
            print(f"[INFO] Collection exists: {collection_name}")

        # 加载 BGE-M3 模型
        print("\n[INFO] Loading BGE-M3 model...")
        model = SentenceTransformer('BAAI/bge-m3')

        # 批量处理
        batch_size = 32
        total_ingested = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]

            # 生成向量
            texts = [chunk["text"] for chunk in batch]
            vectors = model.encode(texts, normalize_embeddings=True)

            # 准备点
            points = []
            for j, chunk in enumerate(batch):
                point = PointStruct(
                    id=hash(chunk["id"]) % (10 ** 8),  # 简单的 ID 转换
                    vector=vectors[j].tolist(),
                    payload={
                        "text": chunk["text"],
                        "source": chunk["source"],
                        "type": chunk["type"],
                        "metadata": chunk["metadata"]
                    }
                )
                points.append(point)

            # 上传
            client.upsert(
                collection_name=collection_name,
                points=points
            )

            total_ingested += len(batch)
            print(f"[OK] Ingested {total_ingested}/{len(chunks)} chunks")

        print(f"\n[SUCCESS] All {len(chunks)} chunks ingested into Qdrant!")

        # 验证
        collection_info = client.get_collection(collection_name)
        print(f"\n[INFO] Collection info:")
        print(f"  - Name: {collection_info.name}")
        print(f"  - Vectors count: {collection_info.vectors_count}")
        print(f"  - Points count: {collection_info.points_count}")

        return True

    except ImportError as e:
        print(f"\n[ERROR] Missing dependencies: {e}")
        print("\n[INFO] Install required packages:")
        print("  pip install qdrant-client sentence-transformers")
        return False

    except Exception as e:
        print(f"\n[ERROR] Failed to ingest: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_ingestion_guide():
    """生成导入指南"""
    guide = """
# Qdrant Ingestion Guide

## Prerequisites

1. **Qdrant Running:**
   ```bash
   # Option A: Docker
   docker run -p 6333:6333 qdrant/qdrant

   # Option B: Docker Compose
   docker-compose up qdrant
   ```

2. **Python Dependencies:**
   ```bash
   pip install qdrant-client sentence-transformers
   ```

3. **BGE-M3 Model:**
   - Will be downloaded automatically on first run
   - Size: ~2.3 GB
   - Location: ~/.cache/huggingface/

## Usage

### Option 1: Run This Script
```bash
python scripts/ingest_to_qdrant.py
```

### Option 2: Manual Ingestion
```python
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import json

# Load chunks
with open('storage/integrated_data/product_rights_chunks.json') as f:
    chunks = json.load(f)

# Connect to Qdrant
client = QdrantClient(url="http://localhost:6333")

# Load model
model = SentenceTransformer('BAAI/bge-m3')

# Ingest
for chunk in chunks:
    vector = model.encode(chunk["text"], normalize_embeddings=True)
    client.upsert(
        collection_name="sales_knowledge",
        points=[{
            "id": hash(chunk["id"]),
            "vector": vector.tolist(),
            "payload": chunk
        }]
    )
```

## Verification

### Test Search
```python
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

client = QdrantClient(url="http://localhost:6333")
model = SentenceTransformer('BAAI/bge-m3')

# Search
query = "信用卡有哪些权益？"
query_vector = model.encode(query, normalize_embeddings=True)

results = client.search(
    collection_name="sales_knowledge",
    query_vector=query_vector.tolist(),
    limit=5
)

for result in results:
    print(f"Score: {result.score:.4f}")
    print(f"Text: {result.payload['text'][:100]}...")
    print()
```

## Troubleshooting

### Issue: Connection refused
**Solution:** Ensure Qdrant is running on port 6333

### Issue: Model download slow
**Solution:** Use mirror or download manually:
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### Issue: Out of memory
**Solution:** Reduce batch size or use smaller model
"""

    guide_file = Path("storage/integrated_data/QDRANT_INGESTION_GUIDE.md")
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(guide)

    print(f"\n[OK] Ingestion guide saved: {guide_file}")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("Qdrant Ingestion Script")
    print("="*70)

    # 加载数据
    chunks_file = Path("storage/integrated_data/product_rights_chunks.json")

    if not chunks_file.exists():
        print(f"\n[ERROR] Chunks file not found: {chunks_file}")
        print("[INFO] Run quick_integrate.py first")
        return

    chunks = load_chunks(chunks_file)

    # 尝试导入
    print("\n[INFO] Attempting to ingest into Qdrant...")
    print("[INFO] This requires:")
    print("  1. Qdrant running on localhost:6333")
    print("  2. qdrant-client and sentence-transformers installed")
    print()

    success = ingest_to_qdrant_simple(chunks)

    if not success:
        print("\n" + "="*70)
        print("Alternative: Manual Ingestion")
        print("="*70)
        print("\n[INFO] Chunks are ready in JSON format")
        print("[INFO] You can ingest them manually using:")
        print("  1. Qdrant Web UI (http://localhost:6333/dashboard)")
        print("  2. Custom Python script")
        print("  3. Existing ingestion pipeline")

        # 生成指南
        generate_ingestion_guide()

    print("\n" + "="*70)
    print("Ingestion Complete")
    print("="*70)


if __name__ == "__main__":
    main()
