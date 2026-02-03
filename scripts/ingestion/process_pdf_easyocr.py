#!/usr/bin/env python3
"""
PDF OCR Processing with EasyOCR
Stable solution for Windows with good Chinese support
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def process_single_pdf_easyocr(pdf_path: Path, output_dir: Path) -> Dict[str, Any]:
    """Process a single PDF with EasyOCR"""
    try:
        import easyocr
        import fitz  # PyMuPDF

        print(f"\n{'='*70}")
        print(f"Processing: {pdf_path.name}")
        print(f"{'='*70}")

        # Initialize EasyOCR (Chinese + English)
        print("[INFO] Initializing EasyOCR (first run will download models)...")
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

        # Open PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"[INFO] Total pages: {total_pages}")

        all_text = []

        # Process each page
        for i, page in enumerate(doc):
            try:
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom
                img_path = output_dir / f"temp_page_{i}.png"
                pix.save(img_path)

                # OCR the image
                result = reader.readtext(str(img_path))

                # Extract text
                page_text = []
                for detection in result:
                    # detection format: (bbox, text, confidence)
                    text = detection[1]
                    confidence = detection[2]
                    if confidence > 0.3:  # Filter low confidence
                        page_text.append(text)

                if page_text:
                    all_text.append("\n".join(page_text))

                # Clean up temp image
                if img_path.exists():
                    img_path.unlink()

                # Progress update
                if (i + 1) % 10 == 0 or (i + 1) == total_pages:
                    print(f"[INFO] Processed {i + 1}/{total_pages} pages...")

            except Exception as e:
                print(f"[WARN] Failed to process page {i+1}: {e}")
                continue

        doc.close()

        # Combine all text
        full_text = "\n\n".join(all_text)
        print(f"[OK] Extracted {len(all_text)} pages with text")
        print(f"[OK] Total text length: {len(full_text)} characters")

        return {
            "success": True,
            "pages_processed": len(all_text),
            "total_pages": total_pages,
            "text": full_text
        }

    except Exception as e:
        print(f"[ERROR] Failed to process PDF: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def extract_chunks(text: str, book_type: str, filename: str) -> List[Dict[str, Any]]:
    """Extract semantic chunks from text"""
    chunks = []

    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]

    print(f"[INFO] Found {len(paragraphs)} paragraphs")

    # Pattern matching for cases and techniques
    case_pattern = r'(?:案例|实例|场景)[\s\d]*[:：]?\s*(.{20,500})'
    dialogue_pattern = r'(?:客户|顾客)[:：]\s*(.{10,200})\s*(?:销售|我)[:：]\s*(.{10,200})'
    technique_pattern = r'(?:技巧|方法|策略)[\s\d]*[:：]?\s*(.{20,300})'

    chunk_id = 0

    for para in paragraphs:
        # Check for case patterns
        case_matches = list(re.finditer(case_pattern, para, re.DOTALL))
        dialogue_matches = list(re.finditer(dialogue_pattern, para))
        technique_matches = list(re.finditer(technique_pattern, para, re.DOTALL))

        if case_matches or dialogue_matches:
            # This is a case/dialogue
            chunk_id += 1
            chunks.append({
                "id": f"{book_type}_case_{chunk_id}",
                "text": para,
                "source": filename,
                "type": "champion_case",
                "metadata": {
                    "book_type": book_type,
                    "extracted_date": datetime.now().isoformat()
                }
            })
        elif technique_matches:
            # This is a technique
            chunk_id += 1
            chunks.append({
                "id": f"{book_type}_technique_{chunk_id}",
                "text": para,
                "source": filename,
                "type": "sales_technique",
                "metadata": {
                    "book_type": book_type,
                    "extracted_date": datetime.now().isoformat()
                }
            })
        elif len(para) > 100 and len(para) < 1000:
            # General knowledge
            chunk_id += 1
            chunks.append({
                "id": f"{book_type}_knowledge_{chunk_id}",
                "text": para,
                "source": filename,
                "type": "sales_knowledge",
                "metadata": {
                    "book_type": book_type,
                    "extracted_date": datetime.now().isoformat()
                }
            })

    print(f"[OK] Created {len(chunks)} semantic chunks")
    return chunks


def main():
    """Main processing function"""
    # Setup paths
    pdf_dir = Path("销冠能力复制数据库/销售成交营销SOP和话术")
    output_dir = Path("data/processed/books")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Books to process
    books = [
        {"filename": "《绝对成交》谈判大师.pdf", "type": "negotiation_master"},
        {"filename": "信用卡销售心态&技巧.pdf", "type": "mindset_skills"},
        {"filename": "信用卡销售技巧培训.pdf", "type": "skills_training"},
        {"filename": "招商银行信用卡销售教程.pdf", "type": "cmb_tutorial"}
    ]

    print("="*70)
    print("PDF Books Processing - EasyOCR Approach")
    print("="*70)

    all_results = []
    total_chunks = 0

    for book in books:
        pdf_path = pdf_dir / book["filename"]

        if not pdf_path.exists():
            print(f"[SKIP] File not found: {pdf_path}")
            continue

        # Process PDF
        result = process_single_pdf_easyocr(pdf_path, output_dir)

        if result["success"]:
            # Extract chunks
            chunks = extract_chunks(result["text"], book["type"], book["filename"])

            # Save chunks
            output_file = output_dir / f"{book['type']}_chunks.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)

            print(f"[OK] Saved {len(chunks)} chunks to {output_file}")

            all_results.append({
                "book": book["filename"],
                "status": "success",
                "pages_processed": result["pages_processed"],
                "chunks_created": len(chunks)
            })

            total_chunks += len(chunks)
        else:
            all_results.append({
                "book": book["filename"],
                "status": "failed",
                "error": result.get("error", "Unknown error")
            })

    # Summary
    print("\n" + "="*70)
    print("Processing Summary")
    print("="*70)
    print(f"Books processed: {len([r for r in all_results if r['status'] == 'success'])}/{len(books)}")
    print(f"Total chunks created: {total_chunks}")

    for result in all_results:
        status_icon = "[OK]" if result["status"] == "success" else "[FAIL]"
        chunks = result.get("chunks_created", 0)
        print(f"  {status_icon} {result['book']}: {chunks} chunks")

    # Save summary
    summary_file = output_dir / "processing_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_books": len(books),
            "successful": len([r for r in all_results if r['status'] == 'success']),
            "total_chunks": total_chunks,
            "results": all_results,
            "timestamp": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Summary saved to: {summary_file}")

    if total_chunks > 0:
        print("\n[SUCCESS] Book processing complete!")
        print("Next step: Run integration script to merge with existing knowledge base")
    else:
        print("\n[WARNING] No chunks extracted. Check PDF files and OCR results.")


if __name__ == "__main__":
    main()
