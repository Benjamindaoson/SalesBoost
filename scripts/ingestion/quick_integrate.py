#!/usr/bin/env python3
"""
Quick Data Integration Script - Simplified Version
快速数据集成脚本 - 简化版

可以立即运行，不需要复杂的依赖
"""

import json
from pathlib import Path
from datetime import datetime
import pandas as pd
from tqdm import tqdm


class QuickIntegration:
    """快速集成"""

    def __init__(self):
        self.cleaned_data_dir = Path("销冠能力复制数据库/cleaned_data_20260201_001")
        self.product_rights_dir = self.cleaned_data_dir / "product_rights"
        self.sales_recordings_dir = self.cleaned_data_dir / "sales_recordings"
        self.output_dir = Path("storage/integrated_data")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            "product_rights_chunks": 0,
            "sales_recordings_files": 0,
            "total_chunks": 0
        }

    def process_product_rights(self):
        """处理产品权益表格"""
        print("\n" + "="*70)
        print("Task 1: Processing Product Rights Tables")
        print("="*70)

        csv_files = list(self.product_rights_dir.glob("*.csv"))
        print(f"\n[INFO] Found {len(csv_files)} CSV files")

        all_chunks = []

        for csv_file in tqdm(csv_files, desc="Processing CSV"):
            try:
                df = pd.read_csv(csv_file, encoding='utf-8-sig')
                print(f"\n[INFO] {csv_file.name}: {len(df)} rows")

                for idx, row in df.iterrows():
                    text_parts = []
                    for col in df.columns:
                        value = row[col]
                        if pd.notna(value) and str(value).strip():
                            text_parts.append(f"{col}: {value}")

                    if text_parts:
                        chunk = {
                            "id": f"product_{csv_file.stem}_{idx}",
                            "text": "\n".join(text_parts),
                            "source": csv_file.name,
                            "type": "product_knowledge",
                            "metadata": {
                                "file": csv_file.name,
                                "row": idx,
                                "category": "product_rights",
                                "date": datetime.now().isoformat()
                            }
                        }
                        all_chunks.append(chunk)

                print(f"  [OK] Created {len(df)} chunks")

            except Exception as e:
                print(f"  [ERROR] {csv_file.name}: {e}")

        # 保存
        output_file = self.output_dir / "product_rights_chunks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)

        self.stats["product_rights_chunks"] = len(all_chunks)
        print(f"\n[OK] Total: {len(all_chunks)} chunks")
        print(f"[OK] Saved: {output_file}")

        return all_chunks

    def process_sales_recordings(self):
        """处理销售录音（生成元数据）"""
        print("\n" + "="*70)
        print("Task 2: Processing Sales Recordings Metadata")
        print("="*70)

        mp3_files = list(self.sales_recordings_dir.glob("*.mp3"))
        print(f"\n[INFO] Found {len(mp3_files)} MP3 files")

        recordings_info = []

        for mp3_file in tqdm(mp3_files, desc="Processing MP3"):
            try:
                size_mb = mp3_file.stat().st_size / (1024 * 1024)

                info = {
                    "id": f"recording_{mp3_file.stem}",
                    "file": mp3_file.name,
                    "path": str(mp3_file),
                    "size_mb": round(size_mb, 2),
                    "status": "ready_for_transcription",
                    "metadata": {
                        "category": "sales_dialogue",
                        "date": datetime.now().isoformat()
                    },
                    "notes": "需要转录服务: OpenAI Whisper / 阿里云语音识别"
                }
                recordings_info.append(info)

                print(f"\n[INFO] {mp3_file.name}: {size_mb:.2f} MB")

            except Exception as e:
                print(f"  [ERROR] {mp3_file.name}: {e}")

        # 保存
        output_file = self.output_dir / "sales_recordings_metadata.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(recordings_info, f, ensure_ascii=False, indent=2)

        self.stats["sales_recordings_files"] = len(recordings_info)
        print(f"\n[OK] Total: {len(recordings_info)} recordings")
        print(f"[OK] Saved: {output_file}")

        return recordings_info

    def generate_report(self, product_chunks, recordings_info):
        """生成报告"""
        print("\n" + "="*70)
        print("Task 3: Generating Integration Report")
        print("="*70)

        self.stats["total_chunks"] = len(product_chunks)

        report = {
            "integration_date": datetime.now().isoformat(),
            "output_directory": str(self.output_dir),
            "statistics": {
                "product_rights": {
                    "chunks_created": len(product_chunks),
                    "ready_for_qdrant": True
                },
                "sales_recordings": {
                    "files_found": len(recordings_info),
                    "ready_for_transcription": True,
                    "transcription_service_needed": "OpenAI Whisper or Alibaba Cloud"
                }
            },
            "next_steps": [
                "1. Review product_rights_chunks.json",
                "2. Ingest chunks into Qdrant using BGE-M3 embeddings",
                "3. Configure transcription service (OPENAI_API_KEY)",
                "4. Run full integration script with transcription",
                "5. Verify retrieval quality with test queries"
            ]
        }

        # JSON 报告
        report_file = self.output_dir / "integration_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 文本报告
        text_report = self.output_dir / "integration_report.txt"
        with open(text_report, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("Data Integration Report - Quick Version\n")
            f.write("="*70 + "\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Output: {self.output_dir}\n\n")

            f.write("="*70 + "\n")
            f.write("Product Rights Tables\n")
            f.write("="*70 + "\n")
            f.write(f"Chunks Created: {len(product_chunks)}\n")
            f.write("Status: ✅ Ready for Qdrant ingestion\n")
            f.write("File: product_rights_chunks.json\n\n")

            f.write("="*70 + "\n")
            f.write("Sales Recordings\n")
            f.write("="*70 + "\n")
            f.write(f"Files Found: {len(recordings_info)}\n")
            f.write("Status: ⏳ Ready for transcription\n")
            f.write("File: sales_recordings_metadata.json\n")
            f.write("Note: 需要配置转录服务\n\n")

            f.write("="*70 + "\n")
            f.write("Next Steps\n")
            f.write("="*70 + "\n")
            for step in report["next_steps"]:
                f.write(f"{step}\n")

            f.write("\n" + "="*70 + "\n")
            f.write("Qdrant Ingestion Command\n")
            f.write("="*70 + "\n")
            f.write("# 使用 Python 脚本导入:\n")
            f.write("python scripts/ingest_to_qdrant.py \\\n")
            f.write("  --input storage/integrated_data/product_rights_chunks.json \\\n")
            f.write("  --collection sales_knowledge \\\n")
            f.write("  --embedding-model BAAI/bge-m3\n\n")

            f.write("="*70 + "\n")
            f.write("Transcription Command\n")
            f.write("="*70 + "\n")
            f.write("# 配置 API Key:\n")
            f.write("export OPENAI_API_KEY=sk-your-key-here\n\n")
            f.write("# 运行完整集成:\n")
            f.write("python scripts/integrate_cleaned_data.py\n")

        print("\n[OK] Reports saved:")
        print(f"  - JSON: {report_file}")
        print(f"  - TXT: {text_report}")

        return report

    def run(self):
        """运行"""
        print("\n" + "="*70)
        print("Quick Data Integration - Starting")
        print("="*70)

        # 任务1: 产品权益
        product_chunks = self.process_product_rights()

        # 任务2: 销售录音
        recordings_info = self.process_sales_recordings()

        # 任务3: 报告
        self.generate_report(product_chunks, recordings_info)

        # 摘要
        print("\n" + "="*70)
        print("Integration Complete")
        print("="*70)
        print(f"\n[OK] Product Rights: {len(product_chunks)} chunks ready")
        print(f"[PENDING] Sales Recordings: {len(recordings_info)} files ready for transcription")
        print(f"\n[OUTPUT] Directory: {self.output_dir}")
        print("\n[DELIVERABLES]")
        print("  - product_rights_chunks.json")
        print("  - sales_recordings_metadata.json")
        print("  - integration_report.json")
        print("  - integration_report.txt")
        print("\n[NEXT] Review integration_report.txt for next steps")


def main():
    """主函数"""
    integration = QuickIntegration()
    integration.run()


if __name__ == "__main__":
    main()
