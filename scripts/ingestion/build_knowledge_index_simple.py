#!/usr/bin/env python3
"""
Build Knowledge Base Index (Simplified)
Import data into ChromaDB with default embeddings

Features:
1. Load semantic chunks
2. Use ChromaDB's default embedding function
3. Import into ChromaDB
4. Create metadata index
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class KnowledgeIndexBuilder:
    """Build knowledge base index with ChromaDB default embeddings"""

    def __init__(self, chroma_path: str = "storage/chromadb"):
        self.chroma_path = Path(chroma_path)
        self.collection_name = "sales_knowledge"
        self.client = None
        self.collection = None

    def initialize_chromadb(self):
        """Initialize ChromaDB client"""
        print("\n=== Initialize ChromaDB ===")

        try:
            import chromadb

            self.client = chromadb.PersistentClient(path=str(self.chroma_path))

            # Delete existing collection for fresh import
            try:
                self.client.delete_collection(self.collection_name)
                print(f"[INFO] Deleted existing collection: {self.collection_name}")
            except:
                pass

            # Create new collection with default embedding function
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Sales knowledge base"}
            )

            print(f"[OK] Created collection: {self.collection_name}")
            print(f"[OK] ChromaDB initialized at: {self.chroma_path}")
            return True

        except ImportError:
            print("[X] ChromaDB not installed")
            return False
        except Exception as e:
            print(f"[X] ChromaDB initialization failed: {e}")
            return False

    def load_chunks(self, chunks_file: Path) -> List[Dict[str, Any]]:
        """Load semantic chunks from file"""
        print("\n=== Load Semantic Chunks ===")

        if not chunks_file.exists():
            print(f"[X] Chunks file not found: {chunks_file}")
            return []

        with open(chunks_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)

        print(f"[OK] Loaded {len(chunks)} chunks")
        return chunks

    def import_to_chromadb(self, chunks: List[Dict[str, Any]]):
        """Import chunks to ChromaDB"""
        print("\n=== Import to ChromaDB ===")

        if not chunks:
            print("[WARN] No chunks to import")
            return

        # Prepare data for ChromaDB
        ids = [chunk['id'] for chunk in chunks]
        documents = [chunk['text'] for chunk in chunks]
        metadatas = []

        for chunk in chunks:
            metadata = {
                "source": chunk['source'],
                "type": chunk['type'],
                "char_count": chunk['char_count'],
                "word_count": chunk['word_count'],
                "created_at": chunk['created_at']
            }

            # Add custom metadata
            if 'metadata' in chunk:
                for key, value in chunk['metadata'].items():
                    # ChromaDB only supports string, int, float, bool
                    if isinstance(value, (str, int, float, bool)):
                        metadata[key] = value
                    else:
                        metadata[key] = str(value)

            metadatas.append(metadata)

        # Import to ChromaDB in batches
        batch_size = 100
        total_imported = 0

        print(f"[INFO] Importing {len(chunks)} chunks...")

        for i in range(0, len(chunks), batch_size):
            batch_end = min(i + batch_size, len(chunks))

            self.collection.add(
                ids=ids[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end]
            )

            total_imported += (batch_end - i)
            print(f"[INFO] Imported {total_imported}/{len(chunks)} chunks")

        print(f"[OK] Successfully imported {total_imported} chunks to ChromaDB")

    def verify_index(self):
        """Verify the knowledge base index"""
        print("\n=== Verify Knowledge Base Index ===")

        try:
            count = self.collection.count()
            print(f"[OK] Total documents in collection: {count}")

            # Test query
            test_query = "如何处理客户的价格异议？"
            print(f"\n[INFO] Test query: {test_query}")

            results = self.collection.query(
                query_texts=[test_query],
                n_results=3
            )

            print(f"[OK] Retrieved {len(results['documents'][0])} results")

            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                print(f"\nResult {i+1}:")
                print(f"  Source: {metadata.get('source', 'unknown')}")
                print(f"  Type: {metadata.get('type', 'unknown')}")
                print(f"  Distance: {distance:.4f}")
                print(f"  Preview: {doc[:100]}...")

            return True

        except Exception as e:
            print(f"[X] Verification failed: {e}")
            return False

    def generate_index_report(self, chunks: List[Dict[str, Any]]):
        """Generate index statistics report"""
        print("\n=== Generate Index Report ===")

        # Count by type
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk['type']
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1

        # Count by source
        source_counts = {}
        for chunk in chunks:
            source = chunk['source']
            source_counts[source] = source_counts.get(source, 0) + 1

        report = {
            "generated_at": datetime.now().isoformat(),
            "total_chunks": len(chunks),
            "total_characters": sum(c['char_count'] for c in chunks),
            "average_chunk_size": sum(c['char_count'] for c in chunks) / len(chunks) if chunks else 0,
            "chunks_by_type": type_counts,
            "chunks_by_source": source_counts,
            "embedding_model": "ChromaDB default (all-MiniLM-L6-v2)",
            "collection_name": self.collection_name,
            "chromadb_path": str(self.chroma_path)
        }

        report_file = Path("data/processed/index_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"[OK] Report saved to: {report_file}")

        print("\nIndex Statistics:")
        print(f"  Total chunks: {report['total_chunks']}")
        print(f"  Total characters: {report['total_characters']:,}")
        print(f"  Average chunk size: {report['average_chunk_size']:.0f} chars")
        print("\nChunks by type:")
        for chunk_type, count in type_counts.items():
            print(f"  {chunk_type}: {count}")


def main():
    """Main function"""
    print("="*70)
    print("Build Knowledge Base Index")
    print("="*70)

    builder = KnowledgeIndexBuilder()

    # 1. Initialize ChromaDB
    if not builder.initialize_chromadb():
        print("\n[X] Failed to initialize ChromaDB")
        return

    # 2. Load semantic chunks
    chunks_file = Path("data/processed/semantic_chunks.json")
    chunks = builder.load_chunks(chunks_file)

    if not chunks:
        print("\n[X] No chunks to process")
        return

    # 3. Import to ChromaDB
    builder.import_to_chromadb(chunks)

    # 4. Verify index
    builder.verify_index()

    # 5. Generate report
    builder.generate_index_report(chunks)

    print("\n" + "="*70)
    print("[OK] Knowledge base index built successfully!")
    print("="*70)
    print("\nNext step:")
    print("1. Develop Agent-data mapping: python scripts/create_agent_interface.py")


if __name__ == "__main__":
    main()
