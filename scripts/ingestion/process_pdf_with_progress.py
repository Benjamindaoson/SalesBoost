#!/usr/bin/env python3
"""
PDF OCR Processing with Qwen-VL-OCR (OpenAI Compatible API)
带实时进度条显示

Author: Claude Sonnet 4.5
Date: 2026-02-01
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import base64
import time
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def image_to_base64(image_path: Path) -> str:
    """Convert image to base64 for API call"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def call_qwen_ocr_api(image_path: Path, api_key: str) -> str:
    """Call Qwen-VL-OCR API using OpenAI compatible format"""
    try:
        from openai import OpenAI

        # Initialize OpenAI client with DashScope endpoint
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        # Convert image to base64
        image_base64 = image_to_base64(image_path)

        # Call API
        completion = client.chat.completions.create(
            model="qwen-vl-ocr-latest",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            },
                        },
                        {
                            "type": "text",
                            "text": "请识别图片中的所有文字内容，保持原有格式和结构。"
                        },
                    ],
                },
            ],
        )

        return completion.choices[0].message.content

    except Exception as e:
        return ""


def process_single_pdf_qwen(pdf_path: Path, output_dir: Path, api_key: str) -> Dict[str, Any]:
    """Process a single PDF with Qwen-VL-OCR"""
    try:
        import fitz  # PyMuPDF

        print(f"\n{'='*70}")
        print(f"Processing: {pdf_path.name}")
        print(f"{'='*70}")

        # Open PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"Total pages: {total_pages}")

        all_text = []

        # Process each page with progress bar
        with tqdm(total=total_pages, desc=f"OCR {pdf_path.name}", unit="page") as pbar:
            for i, page in enumerate(doc):
                try:
                    # Convert page to image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom
                    img_path = output_dir / f"temp_page_{i}.png"
                    pix.save(img_path)

                    # Call Qwen-VL-OCR API
                    text = call_qwen_ocr_api(img_path, api_key)

                    if text:
                        all_text.append(text)
                        pbar.set_postfix({"chars": len(text), "pages_ok": len(all_text)})

                    # Clean up temp image
                    if img_path.exists():
                        img_path.unlink()

                    # Update progress bar
                    pbar.update(1)

                    # Rate limiting
                    time.sleep(0.5)

                except Exception as e:
                    pbar.set_postfix({"error": str(e)[:30]})
                    pbar.update(1)
                    continue

        doc.close()

        # Combine all text
        full_text = "\n\n".join(all_text)
        print(f"✓ Extracted {len(all_text)}/{total_pages} pages")
        print(f"✓ Total text: {len(full_text)} characters")

        return {
            "success": True,
            "pages_processed": len(all_text),
            "total_pages": total_pages,
            "text": full_text
        }

    except Exception as e:
        print(f"✗ Failed: {e}")
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

    return chunks


def main():
    """Main processing function"""
    # Setup paths
    pdf_dir = Path("销冠能力复制数据库/销售成交营销SOP和话术")
    output_dir = Path("data/processed/books")
    output_dir.mkdir(parents=True, exist_ok=True)

    # API configuration
    api_key = "sk-b4b8bc7b72c64d04b799239834e6784b"

    # Books to process
    books = [
        {"filename": "《绝对成交》谈判大师.pdf", "type": "negotiation_master"},
        {"filename": "信用卡销售心态&技巧.pdf", "type": "mindset_skills"},
        {"filename": "信用卡销售技巧培训.pdf", "type": "skills_training"},
        {"filename": "招商银行信用卡销售教程.pdf", "type": "cmb_tutorial"}
    ]

    print("="*70)
    print("PDF Books Processing - Qwen-VL-OCR (OpenAI Compatible)")
    print("="*70)
    print()

    all_results = []
    total_chunks = 0

    # Overall progress
    with tqdm(total=len(books), desc="Overall Progress", unit="book", position=0) as overall_pbar:
        for book in books:
            pdf_path = pdf_dir / book["filename"]

            if not pdf_path.exists():
                print(f"✗ File not found: {pdf_path}")
                overall_pbar.update(1)
                continue

            # Process PDF
            result = process_single_pdf_qwen(pdf_path, output_dir, api_key)

            if result["success"]:
                # Extract chunks
                print(f"Extracting semantic chunks...")
                chunks = extract_chunks(result["text"], book["type"], book["filename"])

                # Save chunks
                output_file = output_dir / f"{book['type']}_chunks.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=2)

                print(f"✓ Saved {len(chunks)} chunks to {output_file.name}")
                print()

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

            overall_pbar.update(1)

    # Summary
    print("\n" + "="*70)
    print("Processing Summary")
    print("="*70)
    successful = len([r for r in all_results if r['status'] == 'success'])
    print(f"Books processed: {successful}/{len(books)}")
    print(f"Total chunks created: {total_chunks}")
    print()

    for result in all_results:
        status_icon = "✓" if result["status"] == "success" else "✗"
        chunks = result.get("chunks_created", 0)
        print(f"  {status_icon} {result['book']}: {chunks} chunks")

    # Save summary
    summary_file = output_dir / "processing_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_books": len(books),
            "successful": successful,
            "total_chunks": total_chunks,
            "results": all_results,
            "timestamp": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Summary saved to: {summary_file}")

    if total_chunks > 0:
        print("\n" + "="*70)
        print("SUCCESS! Book processing complete!")
        print("="*70)
        print(f"Knowledge base expansion: 375 → {375 + total_chunks} chunks")
        print(f"Growth rate: {(total_chunks / 375 * 100):.1f}%")
        print("\nNext step: Run integration script to merge with existing knowledge base")
    else:
        print("\n✗ WARNING: No chunks extracted. Check PDF files and API key.")


if __name__ == "__main__":
    main()
