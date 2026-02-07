#!/usr/bin/env python3
"""
Verify Qdrant Ingestion
验证 Qdrant 数据导入
"""

import requests

def verify_collection():
    """验证集合状态"""
    print("\n" + "="*70)
    print("Verifying Qdrant Collection")
    print("="*70)

    # 创建 session 并禁用代理
    session = requests.Session()
    session.trust_env = False

    qdrant_url = "http://localhost:6333"
    collection_name = "sales_knowledge"

    try:
        # 获取集合信息
        response = session.get(f"{qdrant_url}/collections/{collection_name}")

        if response.status_code == 200:
            data = response.json()
            result = data.get("result", {})

            print(f"\n[OK] Collection: {collection_name}")
            print(f"  - Status: {result.get('status', 'unknown')}")
            print(f"  - Vectors count: {result.get('vectors_count', 0)}")
            print(f"  - Points count: {result.get('points_count', 0)}")
            print(f"  - Indexed vectors: {result.get('indexed_vectors_count', 0)}")

            # 获取配置信息
            config = result.get('config', {})
            params = config.get('params', {})
            vectors_config = params.get('vectors', {})

            if 'text' in vectors_config:
                text_config = vectors_config['text']
                print("\n[INFO] Vector Configuration:")
                print(f"  - Dimension: {text_config.get('size', 'unknown')}")
                print(f"  - Distance: {text_config.get('distance', 'unknown')}")

            # 验证数据
            points_count = result.get('points_count', 0)
            if points_count > 0:
                print(f"\n[SUCCESS] Ingestion verified: {points_count} points in collection")
                return True
            else:
                print("\n[WARN] Collection exists but has no points")
                return False
        else:
            print(f"\n[ERROR] Failed to get collection: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_collection()

    if success:
        print("\n" + "="*70)
        print("Verification Complete - Data Successfully Ingested")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("Verification Failed")
        print("="*70)
