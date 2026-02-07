#!/usr/bin/env python3
"""
PDF Books OCR Processing Script
Extract and structure knowledge from professional sales books

Books to process:
1. 《绝对成交》谈判大师.pdf (46MB)
2. 信用卡销售心态&技巧.pdf (11MB)
3. 信用卡销售技巧培训.pdf (7.5MB)
4. 招商银行信用卡销售教程.pdf (6.6MB)

Author: Claude Sonnet 4.5
Date: 2026-02-01
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class PDFBookProcessor:
    """Process PDF sales books with OCR and structure extraction"""

    def __init__(self, pdf_dir: str = "销冠能力复制数据库/销售成交营销SOP和话术"):
        self.pdf_dir = Path(pdf_dir)
        self.output_dir = Path("data/processed/books")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Books to process
        self.books = [
            {
                "filename": "《绝对成交》谈判大师.pdf",
                "type": "negotiation_master",
                "priority": 1,
                "expected_cases": 50
            },
            {
                "filename": "信用卡销售心态&技巧.pdf",
                "type": "mindset_skills",
                "priority": 2,
                "expected_cases": 30
            },
            {
                "filename": "信用卡销售技巧培训.pdf",
                "type": "skills_training",
                "priority": 3,
                "expected_cases": 40
            },
            {
                "filename": "招商银行信用卡销售教程.pdf",
                "type": "cmb_tutorial",
                "priority": 4,
                "expected_cases": 35
            }
        ]

    def check_ocr_dependencies(self) -> Dict[str, bool]:
        """Check which OCR libraries are available"""
        dependencies = {
            "paddleocr": False,
            "pytesseract": False,
            "pdfplumber": False,
            "pymupdf": False
        }

        try:
            import paddleocr
            dependencies["paddleocr"] = True
        except ImportError:
            pass

        try:
            import pytesseract
            dependencies["pytesseract"] = True
        except ImportError:
            pass

        try:
            import pdfplumber
            dependencies["pdfplumber"] = True
        except ImportError:
            pass

        try:
            import fitz  # PyMuPDF
            dependencies["pymupdf"] = True
        except ImportError:
            pass

        return dependencies

    def extract_text_pdfplumber(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract text using pdfplumber (best for text-based PDFs)"""
        try:
            import pdfplumber

            pages = []
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        pages.append({
                            "page_num": i + 1,
                            "text": text,
                            "method": "pdfplumber"
                        })

            print(f"[OK] Extracted {len(pages)} pages using pdfplumber")
            return pages

        except Exception as e:
            print(f"[WARN] pdfplumber extraction failed: {e}")
            return []

    def extract_text_pymupdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract text using PyMuPDF (fallback method)"""
        try:
            import fitz  # PyMuPDF

            pages = []
            doc = fitz.open(pdf_path)

            for i, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    pages.append({
                        "page_num": i + 1,
                        "text": text,
                        "method": "pymupdf"
                    })

            doc.close()
            print(f"[OK] Extracted {len(pages)} pages using PyMuPDF")
            return pages

        except Exception as e:
            print(f"[WARN] PyMuPDF extraction failed: {e}")
            return []

    def extract_text_paddleocr(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract text using PaddleOCR (for scanned PDFs)"""
        try:
            from paddleocr import PaddleOCR
            import fitz  # PyMuPDF for PDF to image conversion

            print("[INFO] Initializing PaddleOCR (this may take a moment)...")
            ocr = PaddleOCR(use_textline_orientation=True, lang='ch')

            pages = []
            doc = fitz.open(pdf_path)

            for i, page in enumerate(doc):
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                img_path = self.output_dir / f"temp_page_{i}.png"
                pix.save(img_path)

                # OCR the image
                result = ocr.predict(str(img_path))

                # Extract text from OCR result
                text_lines = []
                if result and result[0]:
                    for line in result[0]:
                        text_lines.append(line[1][0])

                text = "\n".join(text_lines)

                if text.strip():
                    pages.append({
                        "page_num": i + 1,
                        "text": text,
                        "method": "paddleocr"
                    })

                # Clean up temp image
                img_path.unlink()

                if (i + 1) % 10 == 0:
                    print(f"[INFO] Processed {i + 1}/{len(doc)} pages...")

            doc.close()
            print(f"[OK] Extracted {len(pages)} pages using PaddleOCR")
            return pages

        except Exception as e:
            print(f"[WARN] PaddleOCR extraction failed: {e}")
            return []

    def extract_text_from_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract text from PDF using best available method"""
        print(f"\n{'='*70}")
        print(f"Processing: {pdf_path.name}")
        print(f"{'='*70}")

        # Check dependencies
        deps = self.check_ocr_dependencies()
        print(f"[INFO] Available OCR methods: {[k for k, v in deps.items() if v]}")

        # Try methods in order of preference
        pages = []

        # 1. Try pdfplumber first (best for text-based PDFs)
        if deps["pdfplumber"]:
            print("[INFO] Trying pdfplumber...")
            pages = self.extract_text_pdfplumber(pdf_path)

        # 2. Try PyMuPDF if pdfplumber failed
        if not pages and deps["pymupdf"]:
            print("[INFO] Trying PyMuPDF...")
            pages = self.extract_text_pymupdf(pdf_path)

        # 3. Try PaddleOCR for scanned PDFs
        if not pages and deps["paddleocr"]:
            print("[INFO] PDF appears to be scanned, trying PaddleOCR...")
            pages = self.extract_text_paddleocr(pdf_path)

        if not pages:
            print(f"[ERROR] Failed to extract text from {pdf_path.name}")
            print("[HELP] Install dependencies:")
            print("  pip install pdfplumber pymupdf paddlepaddle paddleocr")

        return pages

    def identify_case_patterns(self, text: str) -> List[Dict[str, str]]:
        """Identify sales cases and patterns in text"""
        cases = []

        # Pattern 1: Case markers (案例、实例、场景)
        case_pattern = r'(?:案例|实例|场景)[\s\d]*[:：]?\s*(.{20,500})'
        matches = re.finditer(case_pattern, text, re.DOTALL)
        for match in matches:
            cases.append({
                "type": "case_example",
                "content": match.group(1).strip()
            })

        # Pattern 2: Dialogue patterns (对话、客户说、销售说)
        dialogue_pattern = r'(?:客户|顾客)[:：]\s*(.{10,200})\s*(?:销售|我)[:：]\s*(.{10,200})'
        matches = re.finditer(dialogue_pattern, text)
        for match in matches:
            cases.append({
                "type": "dialogue_example",
                "customer": match.group(1).strip(),
                "sales": match.group(2).strip()
            })

        # Pattern 3: Technique descriptions (技巧、方法、策略)
        technique_pattern = r'(?:技巧|方法|策略)[\s\d]*[:：]?\s*(.{20,300})'
        matches = re.finditer(technique_pattern, text, re.DOTALL)
        for match in matches:
            cases.append({
                "type": "technique",
                "content": match.group(1).strip()
            })

        return cases

    def structure_book_content(self, pages: List[Dict[str, Any]], book_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Structure extracted content into semantic chunks"""
        chunks = []

        # Combine all pages
        full_text = "\n\n".join([p["text"] for p in pages])

        # Split into paragraphs
        paragraphs = [p.strip() for p in full_text.split("\n\n") if len(p.strip()) > 50]

        print(f"[INFO] Found {len(paragraphs)} paragraphs")

        # Identify cases and patterns
        all_cases = []
        for para in paragraphs:
            cases = self.identify_case_patterns(para)
            all_cases.extend(cases)

        print(f"[INFO] Identified {len(all_cases)} cases/patterns")

        # Create chunks from cases
        for i, case in enumerate(all_cases):
            chunk = {
                "id": f"{book_info['type']}_case_{i+1}",
                "text": case.get("content", f"{case.get('customer', '')} | {case.get('sales', '')}"),
                "source": book_info["filename"],
                "type": "champion_case" if case["type"] in ["case_example", "dialogue_example"] else "sales_technique",
                "metadata": {
                    "book_type": book_info["type"],
                    "case_type": case["type"],
                    "extracted_date": datetime.now().isoformat()
                }
            }
            chunks.append(chunk)

        # Also create chunks from long paragraphs (knowledge content)
        for i, para in enumerate(paragraphs):
            if len(para) > 100 and len(para) < 1000:
                chunk = {
                    "id": f"{book_info['type']}_para_{i+1}",
                    "text": para,
                    "source": book_info["filename"],
                    "type": "sales_knowledge",
                    "metadata": {
                        "book_type": book_info["type"],
                        "extracted_date": datetime.now().isoformat()
                    }
                }
                chunks.append(chunk)

        print(f"[OK] Created {len(chunks)} semantic chunks")
        return chunks

    def process_book(self, book_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single book"""
        pdf_path = self.pdf_dir / book_info["filename"]

        if not pdf_path.exists():
            print(f"[SKIP] File not found: {pdf_path}")
            return {
                "book": book_info["filename"],
                "status": "not_found",
                "chunks": []
            }

        # Extract text
        pages = self.extract_text_from_pdf(pdf_path)

        if not pages:
            return {
                "book": book_info["filename"],
                "status": "extraction_failed",
                "chunks": []
            }

        # Structure content
        chunks = self.structure_book_content(pages, book_info)

        # Save chunks
        output_file = self.output_dir / f"{book_info['type']}_chunks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        print(f"[OK] Saved {len(chunks)} chunks to {output_file}")

        return {
            "book": book_info["filename"],
            "status": "success",
            "pages_extracted": len(pages),
            "chunks_created": len(chunks),
            "output_file": str(output_file)
        }

    def process_all_books(self) -> Dict[str, Any]:
        """Process all books"""
        print("="*70)
        print("PDF Books Processing - Sales Knowledge Extraction")
        print("="*70)

        results = []

        for book in self.books:
            result = self.process_book(book)
            results.append(result)

        # Summary
        print("\n" + "="*70)
        print("Processing Summary")
        print("="*70)

        total_chunks = sum(r.get("chunks_created", 0) for r in results)
        successful = sum(1 for r in results if r["status"] == "success")

        print(f"Books processed: {successful}/{len(self.books)}")
        print(f"Total chunks created: {total_chunks}")

        for result in results:
            status_icon = "[OK]" if result["status"] == "success" else "[FAIL]"
            print(f"  {status_icon} {result['book']}: {result.get('chunks_created', 0)} chunks")

        return {
            "total_books": len(self.books),
            "successful": successful,
            "total_chunks": total_chunks,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Main processing function"""
    processor = PDFBookProcessor()

    # Check dependencies first
    deps = processor.check_ocr_dependencies()
    print("\n[INFO] Checking OCR dependencies...")
    for lib, available in deps.items():
        status = "[OK]" if available else "[X]"
        print(f"  {status} {lib}")

    if not any(deps.values()):
        print("\n[ERROR] No OCR libraries available!")
        print("\n[HELP] Install dependencies:")
        print("  pip install pdfplumber pymupdf")
        print("  # For scanned PDFs:")
        print("  pip install paddlepaddle paddleocr")
        return

    # Process all books
    results = processor.process_all_books()

    # Save summary
    summary_file = Path("data/processed/books/processing_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Summary saved to: {summary_file}")

    if results["total_chunks"] > 0:
        print("\n[SUCCESS] Book processing complete!")
        print("Next step: Run integration script to merge with existing knowledge base")
    else:
        print("\n[WARNING] No chunks extracted. Check PDF files and dependencies.")


if __name__ == "__main__":
    main()
