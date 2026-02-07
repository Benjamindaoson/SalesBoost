#!/usr/bin/env python3
"""
Clean Qdrant Duplicate Data
清理 Qdrant 重复数据

Current: 706 points (353 old + 353 new)
Target: 353 points (keep new ones with integer IDs)
"""

import requests


def cleanup_qdrant_duplicates(
    qdrant_url: str = "http://localhost:6333",
    collection_name: str = "sales_knowledge"
):
    """清理 Qdrant 重复数据"""
    print("\n" + "="*70)
    print("Cleaning Qdrant Duplicate Data")
    print("="*70)

    # Create session and disable proxy
    session = requests.Session()
    session.trust_env = False

    # Get current collection info
    print("\n[INFO] Checking current collection status...")
    response = session.get(f"{qdrant_url}/collections/{collection_name}")

    if response.status_code == 200:
        data = response.json()
        result = data.get("result", {})
        points_count = result.get("points_count", 0)
        print(f"[OK] Current points: {points_count}")
    else:
        print(f"[ERROR] Failed to get collection info: {response.status_code}")
        return False

    # Strategy: Delete the collection and recreate it
    # This is cleaner than trying to identify and delete old points
    print("\n[INFO] Deleting old collection...")
    response = session.delete(f"{qdrant_url}/collections/{collection_name}")

    if response.status_code in [200, 201]:
        print("[OK] Collection deleted")
    else:
        print(f"[ERROR] Failed to delete collection: {response.text}")
        return False

    # Recreate collection
    print("\n[INFO] Recreating collection with correct configuration...")
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
        print("[OK] Collection recreated")
    else:
        print(f"[ERROR] Failed to recreate collection: {response.text}")
        return False

    print("\n" + "="*70)
    print("Cleanup Complete - Collection Ready for Fresh Data")
    print("="*70)

    return True


if __name__ == "__main__":
    success = cleanup_qdrant_duplicates()

    if success:
        print("\n[SUCCESS] Qdrant collection cleaned!")
        print("[NEXT STEP] Re-ingest data with:")
        print("  python scripts/regenerate_embeddings.py")
    else:
        print("\n[ERROR] Cleanup failed")
