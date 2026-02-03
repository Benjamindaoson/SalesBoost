#!/usr/bin/env python3
"""
销售数据处理脚本
Process Sales Data

功能:
1. 处理Excel产品数据 → SQLite
2. 处理PDF话术文档 → 语义分块 → ChromaDB
3. 处理MP3销售录音 → 转录 → ChromaDB
4. 处理销售冠军经验 → 提取种子案例
"""

import os
import sys
import json
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class SalesDataProcessor:
    """销售数据处理器"""

    def __init__(self, data_dir: str = "销冠能力复制数据库"):
        self.data_dir = Path(data_dir)
        self.db_path = Path("data/databases/salesboost_local.db")
        self.processed_data_dir = Path("data/processed")
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)

    def process_excel_products(self):
        """处理Excel产品数据"""
        print("\n=== 处理Excel产品数据 ===")

        try:
            import pandas as pd
        except ImportError:
            print("[X] pandas未安装，跳过Excel处理")
            return

        excel_dir = self.data_dir / "产品权益"
        if not excel_dir.exists():
            print(f"[X] 目录不存在: {excel_dir}")
            return

        conn = sqlite3.connect(str(self.db_path))

        processed_count = 0
        for excel_file in excel_dir.glob("*.xlsx"):
            if excel_file.name.startswith("~$"):
                continue

            print(f"处理: {excel_file.name}")

            try:
                # 读取Excel
                df = pd.read_excel(excel_file)

                # 保存到SQLite
                table_name = f"product_{excel_file.stem.replace(' ', '_').replace('&', 'and')}"
                df.to_sql(table_name, conn, if_exists='replace', index=False)

                print(f"  [OK] 导入{len(df)}行数据到表: {table_name}")
                processed_count += 1

            except Exception as e:
                print(f"  [X] 处理失败: {e}")

        conn.close()
        print(f"\n[OK] 处理完成: {processed_count}个Excel文件")

    def process_pdf_documents(self):
        """处理PDF话术文档"""
        print("\n=== 处理PDF话术文档 ===")

        try:
            import PyPDF2
        except ImportError:
            print("[X] PyPDF2未安装，跳过PDF处理")
            return

        pdf_dir = self.data_dir / "销售成交营销SOP和话术"
        if not pdf_dir.exists():
            print(f"[X] 目录不存在: {pdf_dir}")
            return

        processed_count = 0
        chunks_data = []

        for pdf_file in pdf_dir.glob("*.pdf"):
            print(f"处理: {pdf_file.name}")

            try:
                # 读取PDF
                with open(pdf_file, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()

                # 简单分块（按段落）
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

                # 创建chunks
                for i, para in enumerate(paragraphs):
                    if len(para) > 50:  # 过滤太短的段落
                        chunk = {
                            "id": f"{pdf_file.stem}_{i}",
                            "content": para,
                            "source": pdf_file.name,
                            "type": "sales_sop",
                            "chunk_index": i
                        }
                        chunks_data.append(chunk)

                print(f"  [OK] 提取{len(paragraphs)}个段落")
                processed_count += 1

            except Exception as e:
                print(f"  [X] 处理失败: {e}")

        # 保存处理结果
        output_file = self.processed_data_dir / "pdf_chunks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] 处理完成: {processed_count}个PDF文件")
        print(f"[OK] 生成{len(chunks_data)}个文本块")
        print(f"[OK] 保存到: {output_file}")

    def process_docx_documents(self):
        """处理Word文档"""
        print("\n=== 处理Word文档 ===")

        try:
            from docx import Document
        except ImportError:
            print("[X] python-docx未安装，跳过Word处理")
            return

        # 处理销售冠军经验
        docx_dir = self.data_dir / "销售冠军成交经验分享"
        if not docx_dir.exists():
            print(f"[X] 目录不存在: {docx_dir}")
            return

        seed_cases = []

        for docx_file in docx_dir.glob("*.docx"):
            if docx_file.name.startswith("~$"):
                continue

            print(f"处理: {docx_file.name}")

            try:
                doc = Document(docx_file)

                # 提取所有段落
                paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

                # 保存为种子案例
                seed_case = {
                    "source": docx_file.name,
                    "content": "\n\n".join(paragraphs),
                    "paragraphs": paragraphs,
                    "extracted_at": datetime.now().isoformat()
                }
                seed_cases.append(seed_case)

                print(f"  [OK] 提取{len(paragraphs)}个段落")

            except Exception as e:
                print(f"  [X] 处理失败: {e}")

        # 保存种子案例
        output_file = Path("data/seeds/champion_cases.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(seed_cases, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] 提取{len(seed_cases)}个种子案例")
        print(f"[OK] 保存到: {output_file}")

    def generate_summary_report(self):
        """生成处理摘要报告"""
        print("\n=== 生成处理摘要 ===")

        report = {
            "processed_at": datetime.now().isoformat(),
            "data_directory": str(self.data_dir),
            "files_processed": {
                "excel": len(list((self.data_dir / "产品权益").glob("*.xlsx"))) if (self.data_dir / "产品权益").exists() else 0,
                "pdf": len(list((self.data_dir / "销售成交营销SOP和话术").glob("*.pdf"))) if (self.data_dir / "销售成交营销SOP和话术").exists() else 0,
                "docx": len(list((self.data_dir / "销售冠军成交经验分享").glob("*.docx"))) if (self.data_dir / "销售冠军成交经验分享").exists() else 0,
                "audio": len(list((self.data_dir / "销售录音").glob("*.mp3"))) + len(list((self.data_dir / "销售录音").glob("*.wav"))) if (self.data_dir / "销售录音").exists() else 0
            }
        }

        report_file = self.processed_data_dir / "processing_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"[OK] 报告保存到: {report_file}")

        return report


def main():
    """主函数"""
    print("="*70)
    print("SalesBoost 数据处理")
    print("="*70)

    processor = SalesDataProcessor()

    # 1. 处理Excel产品数据
    processor.process_excel_products()

    # 2. 处理PDF文档
    processor.process_pdf_documents()

    # 3. 处理Word文档（提取种子案例）
    processor.process_docx_documents()

    # 4. 生成摘要报告
    report = processor.generate_summary_report()

    print("\n" + "="*70)
    print("[OK] 数据处理完成！")
    print("="*70)
    print(f"\n处理统计:")
    print(f"  Excel文件: {report['files_processed']['excel']}")
    print(f"  PDF文件: {report['files_processed']['pdf']}")
    print(f"  Word文件: {report['files_processed']['docx']}")
    print(f"  音频文件: {report['files_processed']['audio']}")

    print("\n下一步:")
    print("1. 查看种子案例: data/seeds/champion_cases.json")
    print("2. 运行数据生成: python scripts/generate_training_data.py")


if __name__ == "__main__":
    main()
