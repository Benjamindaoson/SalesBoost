#!/usr/bin/env python3
"""
PDF OCR Processing with MinerU + Qwen-VL-OCR Hybrid Approach
Based on user's Option B selection

MinerU: High-quality PDF parsing with multiple backends
Qwen-VL-OCR: Alibaba Cloud vision-language model for OCR fallback

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
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class MinerUQwenProcessor:
    """Process PDFs using MinerU + Qwen-VL-OCR hybrid approach"""

    def __init__(self):
        self.pdf_dir = Path("销冠能力复制数据库/销售成交营销SOP和话术")
        self.output_dir = Path("data/processed/books")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Qwen-VL-OCR API configuration
        self.dashscope_api_key = "sk-b4b8bc7b72c64d04b799239834e6784b"
        self.qwen_api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

        # Books to process
        self.books = [
            {"filename": "《绝对成交》谈判大师.pdf", "type": "negotiation_master"},
            {"filename": "信用卡销售心态&技巧.pdf", "type": "mindset_skills"},
            {"filename": "信用卡销售技巧培训.pdf", "type": "skills_training"},
            {"filename": "招商银行信用卡销售教程.pdf", "type": "cmb_tutorial"}
        ]

        self.mineru_available = False
        self.check_mineru()

    def check_mineru(self) -> bool:
        """Check if MinerU is available"""
        try:
            import magic_pdf
            self.mineru_available = True
            print("[OK] MinerU is available")
            return True
        except ImportError:
            print("[WARN] MinerU not available, will use pure Qwen-VL-OCR")
            return False

    def process_with_mineru(self, pdf_path: Path) -> Dict[str, Any]:
        """Process PDF with MinerU"""
        try:
            from magic_pdf.pipe.UNIPipe import UNIPipe
            from magic_pdf.rw.DiskReaderWriter import DiskReaderWriter

            print(f"[INFO] Processing with MinerU: {pdf_path.name}")

            # Read PDF
            reader = DiskReaderWriter(str(pdf_path.parent))
            pdf_bytes = reader.read(pdf_path.name, DiskReaderWriter.MODE_BIN)

            # Initialize MinerU pipeline
            pipe = UNIPipe(pdf_bytes, {"_pdf_type": ""}, str(self.output_dir))

            # Classify PDF type
            pipe.pipe_classify()

            # Parse PDF (try different methods)
            try:
                # Try OCR method first for scanned PDFs
                pipe.pipe_parse()
            except Exception as e:
                print(f"[WARN] MinerU parsing failed: {e}")
                return {"success": False, "error": str(e)}

            # Get markdown output
            md_content = pipe.pipe_mk_markdown(
                str(self.output_dir),
                drop_mode="none",
                md_make_mode="mm_md"
            )

            if md_content:
                print(f"[OK] MinerU extracted {len(md_content)} characters")
                return {
                    "success": True,
                    "text": md_content,
                    "method": "mineru"
                }
            else:
                return {"success": False, "error": "No content extracted"}

        except Exception as e:
            print(f"[ERROR] MinerU processing failed: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def image_to_base64(self, image_path: Path) -> str:
        """Convert image to base64 for API call"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def process_with_qwen_ocr(self, pdf_path: Path) -> Dict[str, Any]:
        """Process PDF with Qwen-VL-OCR"""
        try:
            import fitz  # PyMuPDF

            print(f"[INFO] Processing with Qwen-VL-OCR: {pdf_path.name}")

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
                    img_path = self.output_dir / f"temp_page_{i}.png"
                    pix.save(img_path)

                    # Call Qwen-VL-OCR API
                    image_base64 = self.image_to_base64(img_path)

                    headers = {
                        "Authorization": f"Bearer {self.dashscope_api_key}",
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

                    response = requests.post(
                        self.qwen_api_url,
                        headers=headers,
                        json=payload,
                        timeout=30
                    )

                    if response.status_code == 200:
                        result = response.json()
                        if "output" in result and "choices" in result["output"]:
                            text = result["output"]["choices"][0]["message"]["content"]
                            all_text.append(text)
                    else:
                        print(f"[WARN] API call failed for page {i+1}: {response.status_code}")

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
                "text": full_text,
                "method": "qwen-vl-ocr"
            }

        except Exception as e:
            print(f"[ERROR] Qwen-VL-OCR processing failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def process_single_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Process a single PDF with hybrid approach"""
        print(f"\n{'='*70}")
        print(f"Processing: {pdf_path.name}")
        print(f"{'='*70}")

        # Try MinerU first if available
        if self.mineru_available:
            print("[INFO] Attempting MinerU processing...")
            result = self.process_with_mineru(pdf_path)
            if result["success"]:
                return result
            else:
                print("[INFO] MinerU failed, falling back to Qwen-VL-OCR...")

        # Fallback to Qwen-VL-OCR
        print("[INFO] Using Qwen-VL-OCR...")
        return self.process_with_qwen_ocr(pdf_path)

    def extract_chunks(self, text: str, book_type: str, filename: str) -> List[Dict[str, Any]]:
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

    def process_all_books(self):
        """Process all books"""
        print("="*70)
        print("PDF Books Processing - MinerU + Qwen-VL-OCR Hybrid")
        print("="*70)

        all_results = []
        total_chunks = 0

        for book in self.books:
            pdf_path = self.pdf_dir / book["filename"]

            if not pdf_path.exists():
                print(f"[SKIP] File not found: {pdf_path}")
                continue

            # Process PDF
            result = self.process_single_pdf(pdf_path)

            if result["success"]:
                # Extract chunks
                chunks = self.extract_chunks(result["text"], book["type"], book["filename"])

                # Save chunks
                output_file = self.output_dir / f"{book['type']}_chunks.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=2)

                print(f"[OK] Saved {len(chunks)} chunks to {output_file}")

                all_results.append({
                    "book": book["filename"],
                    "status": "success",
                    "method": result.get("method", "unknown"),
                    "pages_processed": result.get("pages_processed", 0),
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
        print(f"Books processed: {len([r for r in all_results if r['status'] == 'success'])}/{len(self.books)}")
        print(f"Total chunks created: {total_chunks}")

        for result in all_results:
            status_icon = "[OK]" if result["status"] == "success" else "[FAIL]"
            chunks = result.get("chunks_created", 0)
            method = result.get("method", "N/A")
            print(f"  {status_icon} {result['book']}: {chunks} chunks (method: {method})")

        # Save summary
        summary_file = self.output_dir / "processing_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                "total_books": len(self.books),
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


def main():
    """Main processing function"""
    processor = MinerUQwenProcessor()
    processor.process_all_books()


if __name__ == "__main__":
    main()
