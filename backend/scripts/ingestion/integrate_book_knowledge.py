#!/usr/bin/env python3
"""
Integrate Book Knowledge into Main Knowledge Base
Merge processed book chunks with existing semantic_chunks.json

Author: Claude Sonnet 4.5
Date: 2026-02-01
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class KnowledgeIntegrator:
    """Integrate book knowledge with existing knowledge base"""

    def __init__(self):
        self.main_kb_path = Path("data/processed/semantic_chunks.json")
        self.books_dir = Path("data/processed/books")
        self.backup_dir = Path("data/processed/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def load_existing_knowledge_base(self) -> List[Dict[str, Any]]:
        """Load existing knowledge base"""
        if not self.main_kb_path.exists():
            print(f"[ERROR] Main knowledge base not found: {self.main_kb_path}")
            return []

        with open(self.main_kb_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)

        print(f"[OK] Loaded {len(chunks)} existing chunks")
        return chunks

    def load_book_chunks(self) -> List[Dict[str, Any]]:
        """Load all processed book chunks"""
        all_chunks = []

        if not self.books_dir.exists():
            print(f"[WARN] Books directory not found: {self.books_dir}")
            return []

        # Find all book chunk files
        chunk_files = list(self.books_dir.glob("*_chunks.json"))

        if not chunk_files:
            print(f"[WARN] No book chunk files found in {self.books_dir}")
            return []

        for chunk_file in chunk_files:
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                    all_chunks.extend(chunks)
                    print(f"[OK] Loaded {len(chunks)} chunks from {chunk_file.name}")
            except Exception as e:
                print(f"[ERROR] Failed to load {chunk_file.name}: {e}")

        print(f"[OK] Total book chunks loaded: {len(all_chunks)}")
        return all_chunks

    def deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate chunks based on text similarity"""
        unique_chunks = []
        seen_texts = set()

        for chunk in chunks:
            # Use first 100 characters as fingerprint
            fingerprint = chunk["text"][:100].strip()

            if fingerprint not in seen_texts:
                unique_chunks.append(chunk)
                seen_texts.add(fingerprint)

        removed = len(chunks) - len(unique_chunks)
        if removed > 0:
            print(f"[INFO] Removed {removed} duplicate chunks")

        return unique_chunks

    def validate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean chunks"""
        valid_chunks = []

        for chunk in chunks:
            # Check required fields
            if not all(k in chunk for k in ["text", "source", "type"]):
                print("[WARN] Skipping invalid chunk (missing fields)")
                continue

            # Check text length
            if len(chunk["text"]) < 20:
                print(f"[WARN] Skipping chunk with text too short: {len(chunk['text'])} chars")
                continue

            if len(chunk["text"]) > 5000:
                print(f"[WARN] Truncating chunk with text too long: {len(chunk['text'])} chars")
                chunk["text"] = chunk["text"][:5000]

            valid_chunks.append(chunk)

        removed = len(chunks) - len(valid_chunks)
        if removed > 0:
            print(f"[INFO] Removed {removed} invalid chunks")

        return valid_chunks

    def merge_knowledge_bases(
        self,
        existing_chunks: List[Dict[str, Any]],
        book_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge existing and book chunks"""
        print("\n" + "="*70)
        print("Merging Knowledge Bases")
        print("="*70)

        # Combine chunks
        all_chunks = existing_chunks + book_chunks

        print(f"[INFO] Combined chunks: {len(all_chunks)}")

        # Deduplicate
        all_chunks = self.deduplicate_chunks(all_chunks)

        # Validate
        all_chunks = self.validate_chunks(all_chunks)

        # Sort by type for better organization
        all_chunks.sort(key=lambda x: (x["type"], x.get("source", "")))

        return all_chunks

    def create_backup(self):
        """Create backup of existing knowledge base"""
        if not self.main_kb_path.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"semantic_chunks_backup_{timestamp}.json"

        with open(self.main_kb_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] Backup created: {backup_path}")

    def save_merged_knowledge_base(self, chunks: List[Dict[str, Any]]):
        """Save merged knowledge base"""
        with open(self.main_kb_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        print(f"[OK] Saved {len(chunks)} chunks to {self.main_kb_path}")

    def generate_statistics(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics about the knowledge base"""
        stats = {
            "total_chunks": len(chunks),
            "by_type": {},
            "by_source": {},
            "avg_text_length": 0,
            "total_text_length": 0
        }

        # Count by type
        for chunk in chunks:
            chunk_type = chunk.get("type", "unknown")
            stats["by_type"][chunk_type] = stats["by_type"].get(chunk_type, 0) + 1

            source = chunk.get("source", "unknown")
            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

            stats["total_text_length"] += len(chunk["text"])

        if chunks:
            stats["avg_text_length"] = stats["total_text_length"] / len(chunks)

        return stats

    def integrate(self):
        """Main integration process"""
        print("="*70)
        print("Knowledge Base Integration - Books + Existing Data")
        print("="*70)

        # Load existing knowledge base
        existing_chunks = self.load_existing_knowledge_base()

        if not existing_chunks:
            print("[ERROR] Cannot proceed without existing knowledge base")
            return

        # Load book chunks
        book_chunks = self.load_book_chunks()

        if not book_chunks:
            print("[WARNING] No book chunks to integrate")
            print("[INFO] Existing knowledge base unchanged")
            return

        # Create backup
        print("\n[INFO] Creating backup...")
        self.create_backup()

        # Merge
        merged_chunks = self.merge_knowledge_bases(existing_chunks, book_chunks)

        # Save
        print("\n[INFO] Saving merged knowledge base...")
        self.save_merged_knowledge_base(merged_chunks)

        # Statistics
        print("\n" + "="*70)
        print("Integration Statistics")
        print("="*70)

        stats = self.generate_statistics(merged_chunks)

        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Average text length: {stats['avg_text_length']:.0f} characters")

        print("\nChunks by type:")
        for chunk_type, count in sorted(stats["by_type"].items()):
            print(f"  - {chunk_type}: {count}")

        print("\nTop sources:")
        top_sources = sorted(stats["by_source"].items(), key=lambda x: x[1], reverse=True)[:10]
        for source, count in top_sources:
            print(f"  - {source}: {count}")

        # Growth metrics
        growth = len(merged_chunks) - len(existing_chunks)
        growth_pct = (growth / len(existing_chunks)) * 100 if existing_chunks else 0

        print("\n" + "="*70)
        print("Growth Metrics")
        print("="*70)
        print(f"Before: {len(existing_chunks)} chunks")
        print(f"Added: {len(book_chunks)} book chunks")
        print(f"After: {len(merged_chunks)} chunks")
        print(f"Growth: +{growth} chunks ({growth_pct:.1f}%)")

        print("\n[SUCCESS] Knowledge base integration complete!")
        print("\nNext steps:")
        print("1. Rebuild vector store with new chunks")
        print("2. Test agent responses with expanded knowledge")
        print("3. Monitor query quality improvements")


def main():
    """Main function"""
    integrator = KnowledgeIntegrator()
    integrator.integrate()


if __name__ == "__main__":
    main()
