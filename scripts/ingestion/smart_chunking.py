#!/usr/bin/env python3
"""
Smart Chunking Algorithm
Semantic chunking for better retrieval

Features:
1. Semantic-based chunking (not just character count)
2. Preserve context boundaries (paragraphs, sections)
3. Overlap strategy for continuity
4. Metadata enrichment
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class SmartChunker:
    """Smart semantic chunking for sales knowledge"""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_champion_cases(self, cases_file: Path) -> List[Dict[str, Any]]:
        """Chunk champion sales cases with semantic boundaries"""
        print(f"\n=== Chunking Champion Cases ===")

        with open(cases_file, 'r', encoding='utf-8') as f:
            cases = json.load(f)

        all_chunks = []
        chunk_id = 0

        for case in cases:
            source = case['source']
            paragraphs = case.get('paragraphs', [])

            print(f"Processing: {source} ({len(paragraphs)} paragraphs)")

            # Group paragraphs into semantic chunks
            current_chunk = []
            current_length = 0

            for i, para in enumerate(paragraphs):
                para_length = len(para)

                # Check if this is a section header
                is_header = self._is_section_header(para)

                # If adding this paragraph exceeds chunk_size, save current chunk
                if current_length + para_length > self.chunk_size and current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunk = self._create_chunk(
                            chunk_id=chunk_id,
                            text=chunk_text,
                            source=source,
                            chunk_type="champion_case",
                            metadata={
                                "paragraph_range": f"{i - len(current_chunk)}-{i - 1}",
                                "has_header": any(self._is_section_header(p) for p in current_chunk)
                            }
                        )
                        all_chunks.append(chunk)
                        chunk_id += 1

                    # Keep overlap
                    if len(current_chunk) > 1:
                        current_chunk = current_chunk[-1:]
                        current_length = len(current_chunk[0])
                    else:
                        current_chunk = []
                        current_length = 0

                # Add paragraph to current chunk
                current_chunk.append(para)
                current_length += para_length

                # Force chunk boundary at section headers (except first paragraph)
                if is_header and len(current_chunk) > 1:
                    chunk_text = "\n\n".join(current_chunk[:-1])
                    if len(chunk_text) >= self.min_chunk_size:
                        chunk = self._create_chunk(
                            chunk_id=chunk_id,
                            text=chunk_text,
                            source=source,
                            chunk_type="champion_case",
                            metadata={
                                "paragraph_range": f"{i - len(current_chunk) + 1}-{i - 1}",
                                "has_header": True
                            }
                        )
                        all_chunks.append(chunk)
                        chunk_id += 1

                    # Start new chunk with header
                    current_chunk = [para]
                    current_length = para_length

            # Save remaining chunk
            if current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunk = self._create_chunk(
                        chunk_id=chunk_id,
                        text=chunk_text,
                        source=source,
                        chunk_type="champion_case",
                        metadata={
                            "paragraph_range": f"{len(paragraphs) - len(current_chunk)}-{len(paragraphs) - 1}",
                            "has_header": any(self._is_section_header(p) for p in current_chunk)
                        }
                    )
                    all_chunks.append(chunk)
                    chunk_id += 1

        print(f"[OK] Generated {len(all_chunks)} semantic chunks")
        return all_chunks

    def chunk_generated_scenarios(self, scenarios_file: Path) -> List[Dict[str, Any]]:
        """Chunk generated training scenarios"""
        print(f"\n=== Chunking Generated Scenarios ===")

        with open(scenarios_file, 'r', encoding='utf-8') as f:
            scenarios = json.load(f)

        chunks = []

        for i, scenario in enumerate(scenarios):
            # Each scenario is already a semantic unit
            chunk_text = f"""Customer Query: {scenario['customer_query']}

Sales Response: {scenario['sales_response']}

Objection Type: {scenario['objection_type']}
Effectiveness: {scenario['effectiveness']}
Scenario: {scenario['scenario']}"""

            chunk = self._create_chunk(
                chunk_id=i,
                text=chunk_text,
                source=scenario.get('generated_from', 'generated'),
                chunk_type="training_scenario",
                metadata={
                    "objection_type": scenario['objection_type'],
                    "effectiveness": scenario['effectiveness'],
                    "scenario": scenario['scenario']
                }
            )
            chunks.append(chunk)

        print(f"[OK] Generated {len(chunks)} scenario chunks")
        return chunks

    def chunk_pdf_content(self, pdf_chunks_file: Path) -> List[Dict[str, Any]]:
        """Chunk PDF content with semantic boundaries"""
        print(f"\n=== Chunking PDF Content ===")

        with open(pdf_chunks_file, 'r', encoding='utf-8') as f:
            pdf_chunks = json.load(f)

        if not pdf_chunks:
            print("[WARN] No PDF chunks found")
            return []

        # PDF chunks are already pre-chunked, just add metadata
        enhanced_chunks = []
        for i, chunk in enumerate(pdf_chunks):
            enhanced_chunk = self._create_chunk(
                chunk_id=i,
                text=chunk['content'],
                source=chunk['source'],
                chunk_type="sales_sop",
                metadata={
                    "original_chunk_index": chunk.get('chunk_index', i),
                    "type": chunk.get('type', 'sales_sop')
                }
            )
            enhanced_chunks.append(enhanced_chunk)

        print(f"[OK] Enhanced {len(enhanced_chunks)} PDF chunks")
        return enhanced_chunks

    def _is_section_header(self, text: str) -> bool:
        """Detect if text is a section header"""
        # Headers are typically short and contain specific patterns
        if len(text) > 100:
            return False

        header_patterns = [
            r'^【.*】$',  # Chinese brackets
            r'^\[.*\]$',  # Square brackets
            r'^#+\s',     # Markdown headers
            r'^第[一二三四五六七八九十\d]+[章节部分]',  # Chapter markers
            r'^(营销过程|经验总结|亮点|案例)',  # Common section titles
        ]

        for pattern in header_patterns:
            if re.match(pattern, text.strip()):
                return True

        return False

    def _create_chunk(
        self,
        chunk_id: int,
        text: str,
        source: str,
        chunk_type: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a standardized chunk object"""
        return {
            "id": f"chunk_{chunk_id}",
            "text": text,
            "source": source,
            "type": chunk_type,
            "char_count": len(text),
            "word_count": len(text.split()),
            "metadata": metadata,
            "created_at": datetime.now().isoformat()
        }

    def save_chunks(self, chunks: List[Dict[str, Any]], output_file: Path):
        """Save chunks to JSON file"""
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        print(f"[OK] Saved {len(chunks)} chunks to: {output_file}")

        # Generate statistics
        total_chars = sum(c['char_count'] for c in chunks)
        avg_chars = total_chars / len(chunks) if chunks else 0

        print(f"\nChunk Statistics:")
        print(f"  Total chunks: {len(chunks)}")
        print(f"  Total characters: {total_chars:,}")
        print(f"  Average chunk size: {avg_chars:.0f} chars")
        print(f"  Min chunk size: {min(c['char_count'] for c in chunks) if chunks else 0}")
        print(f"  Max chunk size: {max(c['char_count'] for c in chunks) if chunks else 0}")


def main():
    """Main function"""
    print("="*70)
    print("Smart Chunking Algorithm")
    print("="*70)

    chunker = SmartChunker(
        chunk_size=512,
        chunk_overlap=50,
        min_chunk_size=100
    )

    all_chunks = []
    next_chunk_id = 0

    # 1. Chunk champion cases
    champion_cases_file = Path("data/seeds/champion_cases.json")
    if champion_cases_file.exists():
        champion_chunks = chunker.chunk_champion_cases(champion_cases_file)
        # Update IDs to be globally unique
        for chunk in champion_chunks:
            chunk['id'] = f"chunk_{next_chunk_id}"
            next_chunk_id += 1
        all_chunks.extend(champion_chunks)
    else:
        print(f"[WARN] Champion cases file not found: {champion_cases_file}")

    # 2. Chunk generated scenarios
    generated_dir = Path("storage/generated_data")
    if generated_dir.exists():
        scenario_files = list(generated_dir.glob("generated_scenarios_*.json"))
        if scenario_files:
            # Use the most recent file
            latest_file = max(scenario_files, key=lambda p: p.stat().st_mtime)
            scenario_chunks = chunker.chunk_generated_scenarios(latest_file)
            # Update IDs to be globally unique
            for chunk in scenario_chunks:
                chunk['id'] = f"chunk_{next_chunk_id}"
                next_chunk_id += 1
            all_chunks.extend(scenario_chunks)
        else:
            print(f"[WARN] No generated scenario files found in: {generated_dir}")
    else:
        print(f"[WARN] Generated data directory not found: {generated_dir}")

    # 3. Chunk PDF content
    pdf_chunks_file = Path("data/processed/pdf_chunks.json")
    if pdf_chunks_file.exists():
        pdf_chunks = chunker.chunk_pdf_content(pdf_chunks_file)
        # Update IDs to be globally unique
        for chunk in pdf_chunks:
            chunk['id'] = f"chunk_{next_chunk_id}"
            next_chunk_id += 1
        all_chunks.extend(pdf_chunks)
    else:
        print(f"[WARN] PDF chunks file not found: {pdf_chunks_file}")

    # Save all chunks
    if all_chunks:
        output_file = Path("data/processed/semantic_chunks.json")
        chunker.save_chunks(all_chunks, output_file)

        print("\n" + "="*70)
        print("[OK] Smart chunking complete!")
        print("="*70)
        print(f"\nOutput: {output_file}")
        print("\nNext step:")
        print("1. Build knowledge base index: python scripts/build_knowledge_index.py")
    else:
        print("\n[X] No chunks generated")


if __name__ == "__main__":
    main()
