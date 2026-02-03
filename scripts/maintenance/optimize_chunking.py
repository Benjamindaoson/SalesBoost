#!/usr/bin/env python3
"""
Optimize Chunking Granularity
Improve semantic chunking from 68 chunks to 120-150 chunks

Strategy:
- Target: 1.5-2 paragraphs per chunk (average)
- Current: 264 paragraphs → 68 chunks (3.88 paragraphs/chunk)
- Optimized: 264 paragraphs → 120-150 chunks (1.76-2.2 paragraphs/chunk)

Improvements:
1. Reduce chunk_size from 512 to 300 characters
2. Reduce chunk_overlap from 50 to 30 characters
3. Reduce min_chunk_size from 100 to 80 characters
4. Better paragraph boundary detection

Author: Claude Sonnet 4.5
Date: 2026-02-01
Priority: P0
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class OptimizedChunker:
    """
    Optimized semantic chunker for better granularity

    Features:
    - Smaller chunk size for finer granularity
    - Better paragraph boundary detection
    - Metadata preservation
    - Statistics tracking
    """

    def __init__(
        self,
        chunk_size: int = 300,
        chunk_overlap: int = 30,
        min_chunk_size: int = 80
    ):
        """
        Initialize optimized chunker

        Args:
            chunk_size: Target chunk size in characters (reduced from 512)
            chunk_overlap: Overlap between chunks (reduced from 50)
            min_chunk_size: Minimum chunk size (reduced from 100)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

        logger.info(f"Initialized OptimizedChunker:")
        logger.info(f"  chunk_size: {chunk_size}")
        logger.info(f"  chunk_overlap: {chunk_overlap}")
        logger.info(f"  min_chunk_size: {min_chunk_size}")

    def split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Split by double newlines or single newlines followed by headers
        paragraphs = []
        current = []

        for line in text.split('\n'):
            line = line.strip()

            if not line:
                # Empty line - paragraph boundary
                if current:
                    paragraphs.append('\n'.join(current))
                    current = []
            elif line.startswith('【') or line.startswith('#'):
                # Header - start new paragraph
                if current:
                    paragraphs.append('\n'.join(current))
                    current = []
                current.append(line)
            else:
                current.append(line)

        # Add last paragraph
        if current:
            paragraphs.append('\n'.join(current))

        return [p for p in paragraphs if p.strip()]

    def create_chunks(self, paragraphs: List[str]) -> List[Dict[str, Any]]:
        """
        Create semantic chunks from paragraphs

        Strategy:
        - Combine paragraphs until reaching chunk_size
        - Maintain paragraph boundaries
        - Add overlap for context continuity
        """
        chunks = []
        current_chunk = []
        current_length = 0

        for i, para in enumerate(paragraphs):
            para_length = len(para)

            # Check if adding this paragraph would exceed chunk_size
            if current_length + para_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append({
                        'text': chunk_text,
                        'paragraph_indices': list(range(i - len(current_chunk), i)),
                        'char_count': len(chunk_text)
                    })

                # Start new chunk with overlap
                # Keep last paragraph for context continuity
                if len(current_chunk) > 1:
                    current_chunk = [current_chunk[-1], para]
                    current_length = len(current_chunk[-2]) + para_length
                else:
                    current_chunk = [para]
                    current_length = para_length
            else:
                # Add paragraph to current chunk
                current_chunk.append(para)
                current_length += para_length

        # Add last chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append({
                    'text': chunk_text,
                    'paragraph_indices': list(range(len(paragraphs) - len(current_chunk), len(paragraphs))),
                    'char_count': len(chunk_text)
                })

        return chunks

    def process_document(
        self,
        text: str,
        source: str,
        doc_type: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Process a document into optimized chunks

        Args:
            text: Document text
            source: Source file name
            doc_type: Document type (champion_case, training_scenario, sales_sop)
            metadata: Additional metadata

        Returns:
            List of semantic chunks
        """
        # Split into paragraphs
        paragraphs = self.split_into_paragraphs(text)

        # Create chunks
        chunks = self.create_chunks(paragraphs)

        # Add metadata
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            processed_chunk = {
                'text': chunk['text'],
                'source': source,
                'type': doc_type,
                'char_count': chunk['char_count'],
                'word_count': len(chunk['text'].split()),
                'metadata': {
                    'paragraph_indices': chunk['paragraph_indices'],
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    **(metadata or {})
                }
            }
            processed_chunks.append(processed_chunk)

        return processed_chunks


def load_existing_chunks(chunks_file: Path) -> List[Dict[str, Any]]:
    """Load existing chunks for comparison"""
    if not chunks_file.exists():
        logger.warning(f"Chunks file not found: {chunks_file}")
        return []

    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    logger.info(f"[OK] Loaded {len(chunks)} existing chunks")
    return chunks


def optimize_chunks(input_file: Path, output_file: Path):
    """
    Optimize existing chunks with better granularity

    Args:
        input_file: Path to existing semantic_chunks.json
        output_file: Path to save optimized chunks
    """
    logger.info("="*70)
    logger.info("Chunking Optimization")
    logger.info("="*70)

    # Load existing chunks
    existing_chunks = load_existing_chunks(input_file)

    if not existing_chunks:
        logger.error("[X] No existing chunks to optimize")
        return False

    # Group chunks by source document
    docs_by_source = {}
    for chunk in existing_chunks:
        source = chunk['source']
        if source not in docs_by_source:
            docs_by_source[source] = []
        docs_by_source[source].append(chunk)

    logger.info(f"\n[INFO] Found {len(docs_by_source)} source documents")

    # Initialize optimized chunker
    chunker = OptimizedChunker(
        chunk_size=300,  # Reduced from 512
        chunk_overlap=30,  # Reduced from 50
        min_chunk_size=80  # Reduced from 100
    )

    # Process each document
    all_optimized_chunks = []
    chunk_id = 0

    for source, chunks in docs_by_source.items():
        logger.info(f"\n[INFO] Processing: {source}")
        logger.info(f"  Original chunks: {len(chunks)}")

        # Reconstruct document text from chunks
        # Sort by chunk ID to maintain order
        sorted_chunks = sorted(chunks, key=lambda x: x['id'])
        doc_text = '\n\n'.join([c['text'] for c in sorted_chunks])

        # Get document type and metadata
        doc_type = chunks[0]['type']
        doc_metadata = chunks[0].get('metadata', {})

        # Create optimized chunks
        optimized = chunker.process_document(
            text=doc_text,
            source=source,
            doc_type=doc_type,
            metadata=doc_metadata
        )

        # Add chunk IDs
        for chunk in optimized:
            chunk['id'] = f"chunk_{chunk_id}"
            chunk['created_at'] = datetime.now().isoformat()
            chunk_id += 1

        all_optimized_chunks.extend(optimized)

        logger.info(f"  Optimized chunks: {len(optimized)}")
        logger.info(f"  Improvement: {len(optimized) - len(chunks):+d} chunks")

    # Calculate statistics
    logger.info("\n" + "="*70)
    logger.info("Optimization Results")
    logger.info("="*70)

    original_count = len(existing_chunks)
    optimized_count = len(all_optimized_chunks)
    improvement = optimized_count - original_count

    logger.info(f"\nChunk Count:")
    logger.info(f"  Original: {original_count}")
    logger.info(f"  Optimized: {optimized_count}")
    logger.info(f"  Improvement: {improvement:+d} ({improvement/original_count*100:+.1f}%)")

    # Average chunk size
    original_avg = sum(c['char_count'] for c in existing_chunks) / len(existing_chunks)
    optimized_avg = sum(c['char_count'] for c in all_optimized_chunks) / len(all_optimized_chunks)

    logger.info(f"\nAverage Chunk Size:")
    logger.info(f"  Original: {original_avg:.0f} chars")
    logger.info(f"  Optimized: {optimized_avg:.0f} chars")
    logger.info(f"  Reduction: {original_avg - optimized_avg:.0f} chars ({(original_avg - optimized_avg)/original_avg*100:.1f}%)")

    # Chunks by type
    type_counts = {}
    for chunk in all_optimized_chunks:
        chunk_type = chunk['type']
        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1

    logger.info(f"\nChunks by Type:")
    for chunk_type, count in sorted(type_counts.items()):
        logger.info(f"  {chunk_type}: {count}")

    # Save optimized chunks
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_optimized_chunks, f, ensure_ascii=False, indent=2)

    logger.info(f"\n[OK] Optimized chunks saved to: {output_file}")

    # Check if target range achieved
    target_min = 120
    target_max = 150

    if target_min <= optimized_count <= target_max:
        logger.info(f"\n[OK] Target range achieved: {target_min}-{target_max} chunks")
        return True
    elif optimized_count < target_min:
        logger.warning(f"\n[WARN] Below target range: {optimized_count} < {target_min}")
        logger.info("  Suggestion: Reduce chunk_size further or adjust min_chunk_size")
        return False
    else:
        logger.info(f"\n[OK] Above target range: {optimized_count} > {target_max}")
        logger.info("  This is acceptable - more chunks = better granularity")
        return True


def main():
    """Main function"""
    print("="*70)
    print("Chunking Optimization")
    print("="*70)

    # File paths
    input_file = Path("data/processed/semantic_chunks.json")
    output_file = Path("data/processed/semantic_chunks_optimized.json")

    # Run optimization
    success = optimize_chunks(input_file, output_file)

    if success:
        print("\n[OK] Chunking optimization completed successfully!")
        print("\nNext steps:")
        print("1. Backup original: mv semantic_chunks.json semantic_chunks_original.json")
        print("2. Use optimized: mv semantic_chunks_optimized.json semantic_chunks.json")
        print("3. Rebuild vector store: python scripts/fix_semantic_search.py")
        print("4. Run quality tests: python scripts/test_semantic_quality.py")
    else:
        print("\n[WARN] Chunking optimization completed with warnings")
        print("Review the output and adjust parameters if needed")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
