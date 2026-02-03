#!/usr/bin/env python3
"""
Enhanced Data Processor
Process additional source documents to improve knowledge base coverage

Target: Increase from 68 chunks to 120-150 chunks for 85%+ accuracy

Sources to process:
1. 信用卡销售话术对练(3篇).docx
2. 银行信用卡分期话术技巧.docx
3. Excel product data (convert to text chunks)

Author: Claude Sonnet 4.5
Date: 2026-02-01
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


class EnhancedDataProcessor:
    """Enhanced data processor for additional source documents"""

    def __init__(self, data_dir: str = "销冠能力复制数据库"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_sop_docx_files(self) -> List[Dict[str, Any]]:
        """Process SOP DOCX files"""
        logger.info("\n=== Processing SOP DOCX Files ===")

        try:
            from docx import Document
        except ImportError:
            logger.error("[X] python-docx not installed")
            return []

        sop_dir = self.data_dir / "销售成交营销SOP和话术"
        if not sop_dir.exists():
            logger.error(f"[X] Directory not found: {sop_dir}")
            return []

        all_cases = []

        for docx_file in sop_dir.glob("*.docx"):
            if docx_file.name.startswith("~$"):
                continue

            logger.info(f"Processing: {docx_file.name}")

            try:
                doc = Document(docx_file)

                # Extract paragraphs
                paragraphs = []
                for para in doc.paragraphs:
                    text = para.text.strip()
                    if text:
                        paragraphs.append(text)

                logger.info(f"  [OK] Extracted {len(paragraphs)} paragraphs")

                # Create case entry
                case = {
                    "source": docx_file.name,
                    "paragraphs": paragraphs,
                    "type": "sales_sop",
                    "processed_at": datetime.now().isoformat()
                }

                all_cases.append(case)

            except Exception as e:
                logger.error(f"  [X] Processing failed: {e}")

        logger.info(f"[OK] Processed {len(all_cases)} SOP documents")
        return all_cases

    def process_excel_to_text(self) -> List[Dict[str, Any]]:
        """Convert Excel product data to text chunks"""
        logger.info("\n=== Processing Excel Product Data ===")

        try:
            import pandas as pd
        except ImportError:
            logger.error("[X] pandas not installed")
            return []

        excel_dir = self.data_dir / "产品权益"
        if not excel_dir.exists():
            logger.error(f"[X] Directory not found: {excel_dir}")
            return []

        all_chunks = []

        for excel_file in excel_dir.glob("*.xlsx"):
            if excel_file.name.startswith("~$"):
                continue

            logger.info(f"Processing: {excel_file.name}")

            try:
                # Read Excel
                df = pd.read_excel(excel_file)

                # Convert each row to text
                for idx, row in df.iterrows():
                    # Create text representation
                    text_parts = []
                    for col in df.columns:
                        value = row[col]
                        if pd.notna(value) and str(value).strip():
                            text_parts.append(f"{col}: {value}")

                    if text_parts:
                        text = "\n".join(text_parts)

                        chunk = {
                            "source": excel_file.name,
                            "text": text,
                            "type": "product_info",
                            "row_index": idx,
                            "processed_at": datetime.now().isoformat()
                        }

                        all_chunks.append(chunk)

                logger.info(f"  [OK] Converted {len(df)} rows to text chunks")

            except Exception as e:
                logger.error(f"  [X] Processing failed: {e}")

        logger.info(f"[OK] Processed {len(all_chunks)} product info chunks")
        return all_chunks

    def merge_with_existing_chunks(
        self,
        new_cases: List[Dict[str, Any]],
        new_product_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge new data with existing semantic chunks"""
        logger.info("\n=== Merging with Existing Chunks ===")

        # Load existing chunks
        existing_file = self.output_dir / "semantic_chunks.json"
        if existing_file.exists():
            with open(existing_file, 'r', encoding='utf-8') as f:
                existing_chunks = json.load(f)
            logger.info(f"[OK] Loaded {len(existing_chunks)} existing chunks")
        else:
            existing_chunks = []
            logger.warning("[WARN] No existing chunks found")

        # Process new SOP cases with smart chunking
        from scripts.smart_chunking import SmartChunker

        chunker = SmartChunker(
            chunk_size=300,  # Smaller for better granularity
            chunk_overlap=30,
            min_chunk_size=80
        )

        new_chunks = []
        chunk_id = len(existing_chunks)

        # Chunk SOP documents
        for case in new_cases:
            paragraphs = case['paragraphs']
            source = case['source']

            # Group paragraphs into chunks
            current_chunk = []
            current_length = 0

            for para in paragraphs:
                para_length = len(para)

                if current_length + para_length > 300 and current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    if len(chunk_text) >= 80:
                        chunk = {
                            "id": f"chunk_{chunk_id}",
                            "text": chunk_text,
                            "source": source,
                            "type": "sales_sop",
                            "char_count": len(chunk_text),
                            "word_count": len(chunk_text.split()),
                            "metadata": {},
                            "created_at": datetime.now().isoformat()
                        }
                        new_chunks.append(chunk)
                        chunk_id += 1

                    # Keep overlap
                    if len(current_chunk) > 1:
                        current_chunk = [current_chunk[-1]]
                        current_length = len(current_chunk[0])
                    else:
                        current_chunk = []
                        current_length = 0

                current_chunk.append(para)
                current_length += para_length

            # Save remaining chunk
            if current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                if len(chunk_text) >= 80:
                    chunk = {
                        "id": f"chunk_{chunk_id}",
                        "text": chunk_text,
                        "source": source,
                        "type": "sales_sop",
                        "char_count": len(chunk_text),
                        "word_count": len(chunk_text.split()),
                        "metadata": {},
                        "created_at": datetime.now().isoformat()
                    }
                    new_chunks.append(chunk)
                    chunk_id += 1

        logger.info(f"[OK] Created {len(new_chunks)} SOP chunks")

        # Add product info chunks (filter for meaningful content)
        product_chunks_added = 0
        for product_chunk in new_product_chunks:
            text = product_chunk['text']

            # Only add if text is substantial
            if len(text) >= 80:
                chunk = {
                    "id": f"chunk_{chunk_id}",
                    "text": text,
                    "source": product_chunk['source'],
                    "type": "product_info",
                    "char_count": len(text),
                    "word_count": len(text.split()),
                    "metadata": {"row_index": product_chunk['row_index']},
                    "created_at": datetime.now().isoformat()
                }
                new_chunks.append(chunk)
                chunk_id += 1
                product_chunks_added += 1

        logger.info(f"[OK] Added {product_chunks_added} product info chunks")

        # Merge all chunks
        all_chunks = existing_chunks + new_chunks

        logger.info(f"\n[Summary]")
        logger.info(f"  Existing chunks: {len(existing_chunks)}")
        logger.info(f"  New SOP chunks: {len(new_chunks) - product_chunks_added}")
        logger.info(f"  New product chunks: {product_chunks_added}")
        logger.info(f"  Total chunks: {len(all_chunks)}")

        return all_chunks


def main():
    """Main function"""
    logger.info("="*70)
    logger.info("Enhanced Data Processing")
    logger.info("="*70)

    processor = EnhancedDataProcessor()

    # Process SOP DOCX files
    sop_cases = processor.process_sop_docx_files()

    # Process Excel product data
    product_chunks = processor.process_excel_to_text()

    # Merge with existing chunks
    all_chunks = processor.merge_with_existing_chunks(sop_cases, product_chunks)

    # Save merged chunks
    output_file = Path("data/processed/semantic_chunks_enhanced.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    logger.info(f"\n[OK] Enhanced chunks saved to: {output_file}")

    # Calculate statistics
    type_counts = {}
    for chunk in all_chunks:
        chunk_type = chunk['type']
        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1

    logger.info(f"\nChunk Statistics:")
    logger.info(f"  Total chunks: {len(all_chunks)}")
    for chunk_type, count in sorted(type_counts.items()):
        logger.info(f"  {chunk_type}: {count}")

    avg_size = sum(c['char_count'] for c in all_chunks) / len(all_chunks)
    logger.info(f"  Average chunk size: {avg_size:.0f} chars")

    # Check if target achieved
    target_min = 120
    target_max = 150

    if target_min <= len(all_chunks) <= target_max:
        logger.info(f"\n[OK] Target range achieved: {target_min}-{target_max} chunks")
        success = True
    elif len(all_chunks) > target_max:
        logger.info(f"\n[OK] Exceeded target: {len(all_chunks)} > {target_max} chunks")
        logger.info("  More chunks = better coverage!")
        success = True
    else:
        logger.warning(f"\n[WARN] Below target: {len(all_chunks)} < {target_min} chunks")
        success = False

    logger.info("\n" + "="*70)
    logger.info("[OK] Enhanced data processing complete!")
    logger.info("="*70)

    logger.info("\nNext steps:")
    logger.info("1. Backup original: mv semantic_chunks.json semantic_chunks_backup.json")
    logger.info("2. Use enhanced: mv semantic_chunks_enhanced.json semantic_chunks.json")
    logger.info("3. Rebuild vector store: python scripts/fix_semantic_search.py")
    logger.info("4. Run quality tests: python scripts/test_semantic_quality.py")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
