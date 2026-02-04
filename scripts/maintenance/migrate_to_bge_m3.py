"""
Qdrant Collection Migration Script for BGE-M3

This script migrates existing Qdrant collections to BGE-M3 hybrid format.

Migration Strategy:
1. Create new collection with hybrid vectors (dense + sparse)
2. Re-embed all documents using BGE-M3
3. Copy documents to new collection
4. Optionally delete old collection

Usage:
    # Dry run (preview only)
    python scripts/migrate_to_bge_m3.py --source salesboost --preview

    # Full migration
    python scripts/migrate_to_bge_m3.py --source salesboost --target salesboost_bge_m3

    # Migration with old collection deletion
    python scripts/migrate_to_bge_m3.py --source salesboost --target salesboost_bge_m3 --delete-old
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams, PointStruct, SparseVector
from tqdm import tqdm

from app.agents.study.bge_m3_embedder import BGEM3Embedder
from core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class QdrantMigrator:
    """
    Migrates Qdrant collections to BGE-M3 hybrid format
    """

    def __init__(
        self,
        qdrant_url: str,
        qdrant_api_key: Optional[str] = None,
        batch_size: int = 50,
    ):
        """
        Initialize migrator

        Args:
            qdrant_url: Qdrant server URL
            qdrant_api_key: Qdrant API key (optional)
            batch_size: Batch size for processing
        """
        self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        self.batch_size = batch_size
        self.embedder = None

        logger.info(f"Connected to Qdrant at {qdrant_url}")

    def _get_embedder(self) -> BGEM3Embedder:
        """Lazy load embedder"""
        if self.embedder is None:
            logger.info("Loading BGE-M3 model...")
            self.embedder = BGEM3Embedder()
            logger.info("BGE-M3 model loaded")
        return self.embedder

    def preview_migration(self, source_collection: str) -> Dict[str, Any]:
        """
        Preview migration without making changes

        Args:
            source_collection: Source collection name

        Returns:
            Migration preview information
        """
        try:
            # Get collection info
            collection_info = self.client.get_collection(source_collection)

            # Count points
            count_result = self.client.count(source_collection)
            total_points = count_result.count

            # Get sample points
            sample_points = self.client.scroll(
                collection_name=source_collection,
                limit=5,
                with_payload=True,
                with_vectors=False,
            )[0]

            # Analyze structure
            vector_config = collection_info.config.params.vectors
            has_sparse = hasattr(collection_info.config.params, 'sparse_vectors') and \
                        collection_info.config.params.sparse_vectors is not None

            preview = {
                "source_collection": source_collection,
                "total_documents": total_points,
                "current_vector_size": vector_config.size if hasattr(vector_config, 'size') else "unknown",
                "has_sparse_vectors": has_sparse,
                "needs_migration": not has_sparse or vector_config.size != 768,
                "sample_payloads": [
                    {k: v for k, v in point.payload.items() if k != "text"}
                    for point in sample_points[:3]
                ],
                "estimated_time_minutes": (total_points / self.batch_size) * 0.5,  # ~0.5 min per batch
            }

            return preview

        except Exception as e:
            logger.error(f"Preview failed: {e}")
            raise

    def create_target_collection(
        self,
        target_collection: str,
        overwrite: bool = False
    ):
        """
        Create target collection with BGE-M3 hybrid format

        Args:
            target_collection: Target collection name
            overwrite: Overwrite if exists
        """
        try:
            # Check if exists
            try:
                self.client.get_collection(target_collection)
                if overwrite:
                    logger.warning(f"Deleting existing collection: {target_collection}")
                    self.client.delete_collection(target_collection)
                else:
                    raise ValueError(f"Collection {target_collection} already exists. Use --overwrite to replace.")
            except Exception:
                pass  # Collection doesn't exist, which is fine

            # Create new collection
            logger.info(f"Creating collection: {target_collection}")
            self.client.create_collection(
                collection_name=target_collection,
                vectors_config={
                    "dense": VectorParams(
                        size=768,  # BGE-M3 dense dimension
                        distance=Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams()
                },
            )

            logger.info(f"Collection {target_collection} created successfully")

        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

    async def migrate_collection(
        self,
        source_collection: str,
        target_collection: str,
        overwrite: bool = False,
        show_progress: bool = True,
    ) -> Dict[str, Any]:
        """
        Migrate collection to BGE-M3 format

        Args:
            source_collection: Source collection name
            target_collection: Target collection name
            overwrite: Overwrite target if exists
            show_progress: Show progress bar

        Returns:
            Migration statistics
        """
        # Create target collection
        self.create_target_collection(target_collection, overwrite=overwrite)

        # Get embedder
        embedder = self._get_embedder()

        # Get total count
        count_result = self.client.count(source_collection)
        total_points = count_result.count

        logger.info(f"Migrating {total_points} documents from {source_collection} to {target_collection}")

        # Scroll through all points
        migrated_count = 0
        error_count = 0
        offset = None

        progress_bar = tqdm(total=total_points, desc="Migrating") if show_progress else None

        while True:
            # Fetch batch
            points, next_offset = self.client.scroll(
                collection_name=source_collection,
                limit=self.batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            if not points:
                break

            # Extract texts
            texts = []
            metadatas = []
            ids = []

            for point in points:
                text = point.payload.get("text", "")
                if not text:
                    logger.warning(f"Point {point.id} has no text, skipping")
                    error_count += 1
                    continue

                texts.append(text)
                metadatas.append({k: v for k, v in point.payload.items() if k != "text"})
                ids.append(str(point.id))

            if not texts:
                offset = next_offset
                continue

            try:
                # Generate embeddings
                embeddings = embedder.embed_documents(texts, show_progress=False)

                # Prepare points
                new_points = []
                for i, (text, metadata, doc_id) in enumerate(zip(texts, metadatas, ids)):
                    dense_vec = embeddings["dense"][i].tolist()
                    sparse_dict = embeddings["sparse"][i]

                    # Convert sparse dict to Qdrant format
                    sparse_indices = list(sparse_dict.keys())
                    sparse_values = [sparse_dict[idx] for idx in sparse_indices]

                    point = PointStruct(
                        id=doc_id,
                        vector={
                            "dense": dense_vec,
                            "sparse": SparseVector(
                                indices=sparse_indices,
                                values=sparse_values,
                            ),
                        },
                        payload={
                            "text": text,
                            **metadata,
                        },
                    )
                    new_points.append(point)

                # Upload to target collection
                self.client.upsert(
                    collection_name=target_collection,
                    points=new_points,
                )

                migrated_count += len(new_points)

                if progress_bar:
                    progress_bar.update(len(points))

            except Exception as e:
                logger.error(f"Batch migration failed: {e}")
                error_count += len(points)

            # Update offset
            offset = next_offset
            if offset is None:
                break

        if progress_bar:
            progress_bar.close()

        stats = {
            "source_collection": source_collection,
            "target_collection": target_collection,
            "total_documents": total_points,
            "migrated": migrated_count,
            "errors": error_count,
            "success_rate": (migrated_count / total_points * 100) if total_points > 0 else 0,
        }

        logger.info(
            f"Migration complete: {migrated_count}/{total_points} documents migrated "
            f"({stats['success_rate']:.1f}% success rate)"
        )

        return stats

    def delete_collection(self, collection_name: str):
        """Delete collection"""
        logger.warning(f"Deleting collection: {collection_name}")
        self.client.delete_collection(collection_name)
        logger.info(f"Collection {collection_name} deleted")


async def main():
    parser = argparse.ArgumentParser(
        description="Migrate Qdrant collection to BGE-M3 hybrid format"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Source collection name"
    )
    parser.add_argument(
        "--target",
        help="Target collection name (default: {source}_bge_m3)"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview migration without making changes"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite target collection if exists"
    )
    parser.add_argument(
        "--delete-old",
        action="store_true",
        help="Delete old collection after successful migration"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for processing (default: 50)"
    )
    parser.add_argument(
        "--qdrant-url",
        help="Qdrant URL (default: from config)"
    )

    args = parser.parse_args()

    # Load settings
    settings = get_settings()
    qdrant_url = args.qdrant_url or getattr(settings, "QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = getattr(settings, "QDRANT_API_KEY", None)

    # Initialize migrator
    migrator = QdrantMigrator(
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        batch_size=args.batch_size,
    )

    # Preview mode
    if args.preview:
        logger.info("=== Migration Preview ===")
        preview = migrator.preview_migration(args.source)

        print("\n📊 Migration Preview:")
        print(f"  Source Collection: {preview['source_collection']}")
        print(f"  Total Documents: {preview['total_documents']}")
        print(f"  Current Vector Size: {preview['current_vector_size']}")
        print(f"  Has Sparse Vectors: {preview['has_sparse_vectors']}")
        print(f"  Needs Migration: {preview['needs_migration']}")
        print(f"  Estimated Time: ~{preview['estimated_time_minutes']:.1f} minutes")

        if preview['sample_payloads']:
            print("\n  Sample Metadata:")
            for i, payload in enumerate(preview['sample_payloads'], 1):
                print(f"    {i}. {payload}")

        if not preview['needs_migration']:
            print("\n✅ Collection already uses BGE-M3 format, no migration needed!")
        else:
            print("\n⚠️  Migration recommended. Run without --preview to proceed.")

        return

    # Full migration
    target = args.target or f"{args.source}_bge_m3"

    logger.info("=== Starting Migration ===")
    logger.info(f"Source: {args.source}")
    logger.info(f"Target: {target}")

    # Confirm
    if not args.overwrite:
        response = input("\nProceed with migration? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Migration cancelled")
            return

    # Migrate
    stats = await migrator.migrate_collection(
        source_collection=args.source,
        target_collection=target,
        overwrite=args.overwrite,
        show_progress=True,
    )

    # Print results
    print("\n" + "="*50)
    print("📊 Migration Results:")
    print(f"  Total Documents: {stats['total_documents']}")
    print(f"  Migrated: {stats['migrated']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")
    print("="*50)

    # Delete old collection if requested
    if args.delete_old and stats['success_rate'] > 95:
        response = input(f"\nDelete old collection '{args.source}'? (yes/no): ")
        if response.lower() == "yes":
            migrator.delete_collection(args.source)
            print(f"✅ Old collection '{args.source}' deleted")
    elif args.delete_old:
        logger.warning(
            f"Skipping deletion due to low success rate ({stats['success_rate']:.1f}%)"
        )

    print("\n✅ Migration complete!")
    print("\nTo use the new collection, update your config:")
    print(f"  QDRANT_COLLECTION_NAME={target}")


if __name__ == "__main__":
    asyncio.run(main())
