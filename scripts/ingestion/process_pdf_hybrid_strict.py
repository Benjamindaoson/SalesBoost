#!/usr/bin/env python3
"""
Hybrid PDF Processing - MinerU + Qwen-VL Fallback
混合 PDF 处理 - MinerU 优先，Qwen-VL 兜底

Strategy:
1. Try MinerU (Magic-PDF) first - Fast local processing
2. Fallback to Qwen-VL-OCR if MinerU fails
3. Generate structured knowledge chunks

Author: Claude Sonnet 4.5
Date: 2026-02-01
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class HybridPDFProcessor:
    """混合 PDF 处理器"""

    def __init__(self):
        self.pdf_dir = Path("销冠能力复制数据库/销售成交营销SOP和话术")
        self.output_dir = Path("data/processed/books")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 加载 API Key
        from dotenv import load_dotenv
        load_dotenv()
        self.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")

        # 统计
        self.stats = {
            "total_books": 0,
            "mineru_success": 0,
            "qwen_fallback": 0,
            "failed": 0,
            "total_chunks": 0,
            "processing_time": 0
        }

    def try_mineru(self, pdf_path: Path) -> Optional[str]:
        """尝试使用 MinerU 处理 PDF"""
        print(f"\n[ATTEMPT 1] Trying MinerU (Magic-PDF)...")

        try:
            # 方案1: 使用 magic-pdf 命令行
            import subprocess

            # 检查 magic-pdf 是否安装
            result = subprocess.run(
                ["magic-pdf", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                print(f"  [WARN] magic-pdf not installed")
                return None

            print(f"  [OK] magic-pdf found: {result.stdout.strip()}")

            # 运行 MinerU
            output_file = self.output_dir / f"{pdf_path.stem}_mineru.md"

            cmd = [
                "magic-pdf",
                "-p", str(pdf_path),
                "-o", str(output_file),
                "-m", "auto"  # 自动模式
            ]

            print(f"  [INFO] Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode == 0 and output_file.exists():
                with open(output_file, 'r', encoding='utf-8') as f:
                    text = f.read()

                print(f"  [SUCCESS] MinerU extracted {len(text)} characters")
                return text
            else:
                print(f"  [WARN] MinerU failed: {result.stderr}")
                return None

        except FileNotFoundError:
            print(f"  [WARN] magic-pdf command not found")
            return None
        except subprocess.TimeoutExpired:
            print(f"  [WARN] MinerU timeout (>5 minutes)")
            return None
        except Exception as e:
            print(f"  [WARN] MinerU error: {e}")
            return None

    def try_qwen_ocr(self, pdf_path: Path) -> Optional[str]:
        """尝试使用 Qwen-VL-OCR 处理 PDF"""
        print(f"\n[ATTEMPT 2] Trying Qwen-VL-OCR (Cloud API)...")

        if not self.dashscope_api_key:
            print(f"  [ERROR] DASHSCOPE_API_KEY not configured")
            return None

        try:
            import fitz  # PyMuPDF
            import base64
            from openai import OpenAI

            # 初始化客户端
            client = OpenAI(
                api_key=self.dashscope_api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

            # 打开 PDF
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            print(f"  [INFO] Total pages: {total_pages}")

            # 估算时间
            estimated_time = total_pages * 30  # 30秒/页
            print(f"  [WARN] Estimated time: {estimated_time/60:.1f} minutes")

            if total_pages > 50:
                print(f"  [WARN] Too many pages ({total_pages}), this will take too long")
                print(f"  [INFO] Consider processing first 50 pages only")

                # 询问是否继续
                response = input("  Continue with Qwen-VL-OCR? (y/n): ")
                if response.lower() != 'y':
                    doc.close()
                    return None

            all_text = []

            # 处理每一页（限制前50页）
            max_pages = min(total_pages, 50)

            for i in tqdm(range(max_pages), desc="  OCR Progress"):
                try:
                    page = doc[i]

                    # 转换为图片（降低分辨率以避免超过10MB限制）
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5x zoom
                    img_path = self.output_dir / f"temp_page_{i}.png"
                    pix.save(img_path)

                    # 检查图片大小
                    img_size_mb = img_path.stat().st_size / (1024 * 1024)
                    if img_size_mb > 9:  # 留1MB余量
                        print(f"\n  [WARN] Page {i+1} image too large ({img_size_mb:.2f}MB), reducing quality...")
                        # 重新生成更低分辨率
                        pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
                        pix.save(img_path)

                    # 转换为 base64
                    with open(img_path, 'rb') as f:
                        image_base64 = base64.b64encode(f.read()).decode('utf-8')

                    # 调用 API
                    completion = client.chat.completions.create(
                        model="qwen-vl-ocr-latest",
                        messages=[{
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_base64}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": "请识别图片中的所有文字内容，保持原有格式和结构。"
                                }
                            ]
                        }]
                    )

                    text = completion.choices[0].message.content
                    if text:
                        all_text.append(text)

                    # 清理临时文件
                    if img_path.exists():
                        img_path.unlink()

                    # 速率限制
                    time.sleep(0.5)

                except Exception as e:
                    print(f"\n  [WARN] Page {i+1} failed: {e}")
                    continue

            doc.close()

            if all_text:
                full_text = "\n\n".join(all_text)
                print(f"\n  [SUCCESS] Qwen-VL extracted {len(full_text)} characters from {len(all_text)} pages")

                if max_pages < total_pages:
                    print(f"  [INFO] Processed {max_pages}/{total_pages} pages (limited for time)")

                return full_text
            else:
                print(f"  [ERROR] No text extracted")
                return None

        except Exception as e:
            print(f"  [ERROR] Qwen-VL failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_chunks(self, text: str, book_name: str, book_type: str) -> List[Dict]:
        """从文本中提取知识块"""
        print(f"\n[INFO] Extracting knowledge chunks...")

        chunks = []

        # 按段落分割
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]

        print(f"  [INFO] Found {len(paragraphs)} paragraphs")

        # 简单的分块策略
        chunk_id = 0
        current_chunk = ""

        for para in paragraphs:
            # 如果当前块 + 新段落 < 1000字符，合并
            if len(current_chunk) + len(para) < 1000:
                current_chunk += "\n\n" + para if current_chunk else para
            else:
                # 保存当前块
                if current_chunk:
                    chunk_id += 1
                    chunks.append({
                        "id": f"{book_type}_chunk_{chunk_id}",
                        "text": current_chunk,
                        "source": book_name,
                        "type": "sales_knowledge",
                        "metadata": {
                            "book": book_name,
                            "book_type": book_type,
                            "chunk_index": chunk_id,
                            "extracted_date": datetime.now().isoformat()
                        }
                    })

                # 开始新块
                current_chunk = para

        # 保存最后一块
        if current_chunk:
            chunk_id += 1
            chunks.append({
                "id": f"{book_type}_chunk_{chunk_id}",
                "text": current_chunk,
                "source": book_name,
                "type": "sales_knowledge",
                "metadata": {
                    "book": book_name,
                    "book_type": book_type,
                    "chunk_index": chunk_id,
                    "extracted_date": datetime.now().isoformat()
                }
            })

        print(f"  [OK] Created {len(chunks)} chunks")
        return chunks

    def process_single_book(self, pdf_path: Path, book_type: str) -> Dict[str, Any]:
        """处理单本书"""
        print("\n" + "="*70)
        print(f"Processing: {pdf_path.name}")
        print("="*70)

        start_time = time.time()

        # 尝试 MinerU
        text = self.try_mineru(pdf_path)

        if text:
            method = "mineru"
            self.stats["mineru_success"] += 1
        else:
            # 回退到 Qwen-VL
            text = self.try_qwen_ocr(pdf_path)

            if text:
                method = "qwen_vl"
                self.stats["qwen_fallback"] += 1
            else:
                print(f"\n[FAILED] Both methods failed for {pdf_path.name}")
                self.stats["failed"] += 1
                return {
                    "success": False,
                    "book": pdf_path.name,
                    "error": "Both MinerU and Qwen-VL failed"
                }

        # 提取知识块
        chunks = self.extract_chunks(text, pdf_path.name, book_type)

        # 保存
        output_file = self.output_dir / f"{book_type}_chunks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        # 保存原始文本
        text_file = self.output_dir / f"{book_type}_text.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text)

        processing_time = time.time() - start_time
        self.stats["total_chunks"] += len(chunks)
        self.stats["processing_time"] += processing_time

        print(f"\n[SUCCESS] Processed {pdf_path.name}")
        print(f"  Method: {method}")
        print(f"  Chunks: {len(chunks)}")
        print(f"  Time: {processing_time:.1f}s")
        print(f"  Output: {output_file}")

        return {
            "success": True,
            "book": pdf_path.name,
            "method": method,
            "chunks": len(chunks),
            "time": processing_time,
            "output": str(output_file)
        }

    def run(self):
        """运行处理流程"""
        print("\n" + "="*70)
        print("Hybrid PDF Processing - MinerU + Qwen-VL")
        print("="*70)

        # 书籍列表
        books = [
            {"filename": "《绝对成交》谈判大师.pdf", "type": "negotiation_master"},
            {"filename": "信用卡销售心态&技巧.pdf", "type": "mindset_skills"},
            {"filename": "信用卡销售技巧培训.pdf", "type": "skills_training"},
            {"filename": "招商银行信用卡销售教程.pdf", "type": "cmb_tutorial"}
        ]

        self.stats["total_books"] = len(books)

        results = []

        for book in books:
            pdf_path = self.pdf_dir / book["filename"]

            if not pdf_path.exists():
                print(f"\n[SKIP] File not found: {pdf_path}")
                continue

            result = self.process_single_book(pdf_path, book["type"])
            results.append(result)

        # 生成报告
        self.generate_report(results)

    def generate_report(self, results: List[Dict]):
        """生成处理报告"""
        print("\n" + "="*70)
        print("Processing Summary")
        print("="*70)

        print(f"\nTotal Books: {self.stats['total_books']}")
        print(f"MinerU Success: {self.stats['mineru_success']}")
        print(f"Qwen-VL Fallback: {self.stats['qwen_fallback']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Total Chunks: {self.stats['total_chunks']}")
        print(f"Total Time: {self.stats['processing_time']:.1f}s")

        # 保存报告
        report = {
            "processing_date": datetime.now().isoformat(),
            "statistics": self.stats,
            "results": results
        }

        report_file = self.output_dir / "processing_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] Report saved: {report_file}")

        # 结论
        if self.stats["failed"] == 0:
            print("\n[SUCCESS] All books processed successfully!")
        elif self.stats["mineru_success"] + self.stats["qwen_fallback"] > 0:
            print(f"\n[PARTIAL] {self.stats['mineru_success'] + self.stats['qwen_fallback']}/{self.stats['total_books']} books processed")
        else:
            print("\n[FAILED] No books processed successfully")


def main():
    """主函数"""
    processor = HybridPDFProcessor()
    processor.run()


if __name__ == "__main__":
    main()
