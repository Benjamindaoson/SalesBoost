#!/usr/bin/env python3
"""
PDF OCR Processing with Qwen-VL-OCR
Pure cloud-based approach using Alibaba DashScope API

Author: Claude Sonnet 4.5
Date: 2026-02-01
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import base64
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def image_to_base64(image_path: Path) -> str:
    """Convert image to base64 for API call"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def call_qwen_ocr_api(image_base64: str, api_key: str) -> str:
    """Call Qwen-VL-OCR API"""
    try:
        import requests

        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "qwen-vl-ocr-latest",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "image": f"data:image/png;base64,{image_base64}"
                            },
                            {
                                "text": "请识别图片中的所有文字内容，保持原有格式和结构。"
                            }
                        ]
                    }
                ]
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            if "output" in result and "choices" in result["output"]:
                return result["output"]["choices"][0]["message"]["content"]
            else:
                print(f"[WARN] Unexpected API response format: {result}")
                return ""
        else:
            print(f"[ERROR] API call failed: {response.status_code} - {response.text}")
            return ""

    except Exception as e:
        print(f"[ERROR] API call exception: {e}")
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
        print(f"[INFO] Total pages: {total_pages}")

        all_text = []

        # Process each page
        for i, page in enumerate(doc):
            try:
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_path = output_dir / f"temp_page_{i}.png"
                pix.save(img_path)

                # Call Qwen-VL-OCR API
                image_base64 = image_to_base64(img_path)
                text = call_qwen_ocr_api(image_base64, api_key)

                if text:
                    all_text.append(text)

                # Clean up temp image
                if img_path.exists():
                    img_path.unlink()

                # Progress update
                if (i + 1) % 5 == 0 or (i + 1) == total_pages:
                    print(f"[INFO] Processed {i + 1}/{total_pages} pages...")

                # Rate limiting - be respectful to API
                time.sleep(0.5)

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
    print("PDF Books Processing - Qwen-VL-OCR Cloud Approach")
    print("="*70)

    all_results = []
    total_chunks = 0

    for book in books:
        pdf_path = pdf_dir / book["filename"]

        if not pdf_path.exists():
            print(f"[SKIP] File not found: {pdf_path}")
            continue

        # Process PDF
        result = process_single_pdf_qwen(pdf_path, output_dir, api_key)

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
