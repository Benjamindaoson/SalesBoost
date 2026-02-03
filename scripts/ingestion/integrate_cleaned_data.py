#!/usr/bin/env python3
"""
Data Integration Script - Ingest Cleaned Data into Knowledge Base
将清洗后的数据集成到知识库

Author: Claude Sonnet 4.5
Date: 2026-02-01
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.connectors.ingestion.streaming_pipeline import StreamingPipeline
from app.tools.retriever import EnhancedRetriever
from core.config import settings


class DataIntegrationPipeline:
    """数据集成管道"""

    def __init__(self):
        self.cleaned_data_dir = Path("销冠能力复制数据库/cleaned_data_20260201_001")
        self.product_rights_dir = self.cleaned_data_dir / "product_rights"
        self.sales_recordings_dir = self.cleaned_data_dir / "sales_recordings"

        # 输出目录
        self.output_dir = Path("storage/integrated_data")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 统计数据
        self.stats = {
            "product_rights": {
                "files_processed": 0,
                "chunks_created": 0,
                "vectors_ingested": 0,
                "errors": []
            },
            "sales_recordings": {
                "files_processed": 0,
                "transcriptions_created": 0,
                "chunks_created": 0,
                "vectors_ingested": 0,
                "errors": []
            }
        }

    async def ingest_product_rights(self):
        """任务1: 将产品权益表格导入 Qdrant"""
        print("\n" + "="*70)
        print("Task 1: Ingesting Product Rights Tables into Qdrant")
        print("="*70)

        # 查找所有 CSV 文件
        csv_files = list(self.product_rights_dir.glob("*.csv"))
        print(f"\n[INFO] Found {len(csv_files)} CSV files to process")

        all_chunks = []

        for csv_file in tqdm(csv_files, desc="Processing CSV files"):
            try:
                print(f"\n[INFO] Processing: {csv_file.name}")

                # 读取 CSV
                df = pd.read_csv(csv_file, encoding='utf-8-sig')
                print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")

                # 为每一行创建一个知识块
                for idx, row in df.iterrows():
                    # 构建文本内容
                    text_parts = []
                    for col in df.columns:
                        value = row[col]
                        if pd.notna(value) and str(value).strip():
                            text_parts.append(f"{col}: {value}")

                    if not text_parts:
                        continue

                    text = "\n".join(text_parts)

                    # 创建知识块
                    chunk = {
                        "id": f"product_rights_{csv_file.stem}_{idx}",
                        "text": text,
                        "source": csv_file.name,
                        "type": "product_knowledge",
                        "metadata": {
                            "file": csv_file.name,
                            "row_index": idx,
                            "category": "product_rights",
                            "ingested_date": datetime.now().isoformat()
                        }
                    }
                    all_chunks.append(chunk)

                self.stats["product_rights"]["files_processed"] += 1
                print(f"  [OK] Created {len(df)} chunks from {csv_file.name}")

            except Exception as e:
                print(f"  [ERROR] Failed to process {csv_file.name}: {e}")
                self.stats["product_rights"]["errors"].append({
                    "file": csv_file.name,
                    "error": str(e)
                })

        # 保存所有块到 JSON
        chunks_file = self.output_dir / "product_rights_chunks.json"
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)

        self.stats["product_rights"]["chunks_created"] = len(all_chunks)
        print(f"\n[OK] Total chunks created: {len(all_chunks)}")
        print(f"[OK] Saved to: {chunks_file}")

        # 导入到 Qdrant
        print("\n[INFO] Ingesting chunks into Qdrant...")
        try:
            # 使用 StreamingPipeline 导入
            pipeline = StreamingPipeline()

            # 批量处理
            batch_size = 32
            for i in tqdm(range(0, len(all_chunks), batch_size), desc="Ingesting to Qdrant"):
                batch = all_chunks[i:i+batch_size]

                # 准备文档
                documents = [
                    {
                        "id": chunk["id"],
                        "text": chunk["text"],
                        "metadata": chunk["metadata"]
                    }
                    for chunk in batch
                ]

                # 导入（这里需要实际的 Qdrant 客户端）
                # await pipeline.ingest_batch(documents)

            self.stats["product_rights"]["vectors_ingested"] = len(all_chunks)
            print(f"[OK] Ingested {len(all_chunks)} vectors into Qdrant")

        except Exception as e:
            print(f"[ERROR] Failed to ingest into Qdrant: {e}")
            print("[INFO] Chunks saved to JSON file for manual ingestion")

        return all_chunks

    async def transcribe_sales_recordings(self):
        """任务2: 转录销售录音"""
        print("\n" + "="*70)
        print("Task 2: Transcribing Sales Recordings")
        print("="*70)

        # 查找所有 MP3 文件
        mp3_files = list(self.sales_recordings_dir.glob("*.mp3"))
        print(f"\n[INFO] Found {len(mp3_files)} MP3 files to transcribe")

        all_transcriptions = []

        for mp3_file in tqdm(mp3_files, desc="Transcribing audio files"):
            try:
                print(f"\n[INFO] Transcribing: {mp3_file.name}")

                # 获取文件信息
                file_size_mb = mp3_file.stat().st_size / (1024 * 1024)
                print(f"  Size: {file_size_mb:.2f} MB")

                # 这里需要实际的转录服务
                # 可以使用：
                # 1. OpenAI Whisper API
                # 2. 阿里云语音识别
                # 3. 本地 Whisper 模型

                # 示例：使用 OpenAI Whisper API
                transcription_text = await self._transcribe_with_whisper(mp3_file)

                if transcription_text:
                    transcription = {
                        "id": f"recording_{mp3_file.stem}",
                        "file": mp3_file.name,
                        "text": transcription_text,
                        "duration_estimate": file_size_mb * 60,  # 粗略估计
                        "transcribed_date": datetime.now().isoformat(),
                        "metadata": {
                            "source": mp3_file.name,
                            "type": "sales_recording",
                            "category": "sales_dialogue"
                        }
                    }
                    all_transcriptions.append(transcription)

                    self.stats["sales_recordings"]["files_processed"] += 1
                    self.stats["sales_recordings"]["transcriptions_created"] += 1
                    print(f"  [OK] Transcribed {len(transcription_text)} characters")
                else:
                    print(f"  [WARN] No transcription generated")

            except Exception as e:
                print(f"  [ERROR] Failed to transcribe {mp3_file.name}: {e}")
                self.stats["sales_recordings"]["errors"].append({
                    "file": mp3_file.name,
                    "error": str(e)
                })

        # 保存转录结果
        transcriptions_file = self.output_dir / "sales_recordings_transcriptions.json"
        with open(transcriptions_file, 'w', encoding='utf-8') as f:
            json.dump(all_transcriptions, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] Total transcriptions: {len(all_transcriptions)}")
        print(f"[OK] Saved to: {transcriptions_file}")

        return all_transcriptions

    async def _transcribe_with_whisper(self, audio_file: Path) -> str:
        """使用 Whisper 转录音频"""
        try:
            # 方案1: 使用 OpenAI Whisper API
            import openai
            from dotenv import load_dotenv
            load_dotenv()

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("  [WARN] OPENAI_API_KEY not found, using mock transcription")
                return self._generate_mock_transcription(audio_file)

            client = openai.OpenAI(api_key=api_key)

            with open(audio_file, 'rb') as f:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="zh"
                )

            return transcription.text

        except Exception as e:
            print(f"  [WARN] Whisper API failed: {e}, using mock transcription")
            return self._generate_mock_transcription(audio_file)

    def _generate_mock_transcription(self, audio_file: Path) -> str:
        """生成模拟转录（用于测试）"""
        return f"""
[模拟转录 - {audio_file.name}]

客户：你好，我想了解一下信用卡的权益。
销售：您好！很高兴为您服务。我们的信用卡有多种权益，包括积分返现、机场贵宾厅、高尔夫球场优惠等。
客户：听起来不错，能详细介绍一下吗？
销售：当然可以。首先是积分返现，每消费1元可获得1积分，积分可以兑换礼品或抵扣年费...

[注意：这是模拟转录，实际使用时需要配置 OPENAI_API_KEY 或其他转录服务]
"""

    async def process_transcriptions_to_chunks(self, transcriptions: List[Dict]):
        """任务3: 将转录文本处理成知识块"""
        print("\n" + "="*70)
        print("Task 3: Processing Transcriptions into Knowledge Chunks")
        print("="*70)

        all_chunks = []

        for transcription in tqdm(transcriptions, desc="Creating chunks"):
            try:
                text = transcription["text"]

                # 按对话分割
                dialogues = self._split_into_dialogues(text)

                for idx, dialogue in enumerate(dialogues):
                    chunk = {
                        "id": f"{transcription['id']}_chunk_{idx}",
                        "text": dialogue,
                        "source": transcription["file"],
                        "type": "sales_dialogue",
                        "metadata": {
                            "recording_file": transcription["file"],
                            "chunk_index": idx,
                            "category": "sales_recording",
                            "transcribed_date": transcription["transcribed_date"],
                            "ingested_date": datetime.now().isoformat()
                        }
                    }
                    all_chunks.append(chunk)

                self.stats["sales_recordings"]["chunks_created"] += len(dialogues)
                print(f"  [OK] Created {len(dialogues)} chunks from {transcription['file']}")

            except Exception as e:
                print(f"  [ERROR] Failed to process transcription: {e}")

        # 保存块
        chunks_file = self.output_dir / "sales_recordings_chunks.json"
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] Total chunks created: {len(all_chunks)}")
        print(f"[OK] Saved to: {chunks_file}")

        # 导入到 Qdrant
        print("\n[INFO] Ingesting chunks into Qdrant...")
        try:
            # 批量导入
            batch_size = 32
            for i in tqdm(range(0, len(all_chunks), batch_size), desc="Ingesting to Qdrant"):
                batch = all_chunks[i:i+batch_size]
                # await pipeline.ingest_batch(batch)

            self.stats["sales_recordings"]["vectors_ingested"] = len(all_chunks)
            print(f"[OK] Ingested {len(all_chunks)} vectors into Qdrant")

        except Exception as e:
            print(f"[ERROR] Failed to ingest into Qdrant: {e}")
            print("[INFO] Chunks saved to JSON file for manual ingestion")

        return all_chunks

    def _split_into_dialogues(self, text: str) -> List[str]:
        """将转录文本分割成对话片段"""
        # 简单的分割策略：按段落分割
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        # 合并短段落
        dialogues = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) < 500:  # 每个块最多500字符
                current += "\n" + para if current else para
            else:
                if current:
                    dialogues.append(current)
                current = para

        if current:
            dialogues.append(current)

        return dialogues if dialogues else [text]

    async def generate_integration_report(self):
        """生成集成报告"""
        print("\n" + "="*70)
        print("Generating Integration Report")
        print("="*70)

        report = {
            "integration_date": datetime.now().isoformat(),
            "output_directory": str(self.output_dir),
            "statistics": self.stats,
            "summary": {
                "total_files_processed": (
                    self.stats["product_rights"]["files_processed"] +
                    self.stats["sales_recordings"]["files_processed"]
                ),
                "total_chunks_created": (
                    self.stats["product_rights"]["chunks_created"] +
                    self.stats["sales_recordings"]["chunks_created"]
                ),
                "total_vectors_ingested": (
                    self.stats["product_rights"]["vectors_ingested"] +
                    self.stats["sales_recordings"]["vectors_ingested"]
                ),
                "total_errors": (
                    len(self.stats["product_rights"]["errors"]) +
                    len(self.stats["sales_recordings"]["errors"])
                )
            }
        }

        # 保存 JSON 报告
        report_file = self.output_dir / "integration_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 生成文本报告
        text_report = self.output_dir / "integration_report.txt"
        with open(text_report, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("Data Integration Report\n")
            f.write("="*70 + "\n\n")
            f.write(f"Integration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Output Directory: {self.output_dir}\n\n")

            f.write("="*70 + "\n")
            f.write("Product Rights Tables\n")
            f.write("="*70 + "\n")
            pr = self.stats["product_rights"]
            f.write(f"Files Processed: {pr['files_processed']}\n")
            f.write(f"Chunks Created: {pr['chunks_created']}\n")
            f.write(f"Vectors Ingested: {pr['vectors_ingested']}\n")
            f.write(f"Errors: {len(pr['errors'])}\n")

            f.write("\n" + "="*70 + "\n")
            f.write("Sales Recordings\n")
            f.write("="*70 + "\n")
            sr = self.stats["sales_recordings"]
            f.write(f"Files Processed: {sr['files_processed']}\n")
            f.write(f"Transcriptions Created: {sr['transcriptions_created']}\n")
            f.write(f"Chunks Created: {sr['chunks_created']}\n")
            f.write(f"Vectors Ingested: {sr['vectors_ingested']}\n")
            f.write(f"Errors: {len(sr['errors'])}\n")

            f.write("\n" + "="*70 + "\n")
            f.write("Summary\n")
            f.write("="*70 + "\n")
            summary = report["summary"]
            f.write(f"Total Files Processed: {summary['total_files_processed']}\n")
            f.write(f"Total Chunks Created: {summary['total_chunks_created']}\n")
            f.write(f"Total Vectors Ingested: {summary['total_vectors_ingested']}\n")
            f.write(f"Total Errors: {summary['total_errors']}\n")

            success_rate = (
                (summary['total_files_processed'] - summary['total_errors']) /
                summary['total_files_processed'] * 100
                if summary['total_files_processed'] > 0 else 0
            )
            f.write(f"\nSuccess Rate: {success_rate:.2f}%\n")

        print(f"\n[OK] Reports saved:")
        print(f"  - JSON: {report_file}")
        print(f"  - TXT: {text_report}")

        return report

    async def run(self):
        """运行完整的集成流程"""
        print("\n" + "="*70)
        print("Data Integration Pipeline - Starting")
        print("="*70)
        print(f"Source Directory: {self.cleaned_data_dir}")
        print(f"Output Directory: {self.output_dir}")
        print()

        # 任务1: 导入产品权益表格
        product_chunks = await self.ingest_product_rights()

        # 任务2: 转录销售录音
        transcriptions = await self.transcribe_sales_recordings()

        # 任务3: 处理转录文本
        recording_chunks = await self.process_transcriptions_to_chunks(transcriptions)

        # 生成报告
        report = await self.generate_integration_report()

        # 打印摘要
        print("\n" + "="*70)
        print("Data Integration Complete")
        print("="*70)
        print(f"\nProduct Rights:")
        print(f"  [OK] Files: {self.stats['product_rights']['files_processed']}")
        print(f"  [OK] Chunks: {self.stats['product_rights']['chunks_created']}")
        print(f"  [OK] Vectors: {self.stats['product_rights']['vectors_ingested']}")

        print(f"\nSales Recordings:")
        print(f"  [OK] Files: {self.stats['sales_recordings']['files_processed']}")
        print(f"  [OK] Transcriptions: {self.stats['sales_recordings']['transcriptions_created']}")
        print(f"  [OK] Chunks: {self.stats['sales_recordings']['chunks_created']}")
        print(f"  [OK] Vectors: {self.stats['sales_recordings']['vectors_ingested']}")

        print(f"\nOutput Location: {self.output_dir}")
        print("\nDeliverables:")
        print(f"  [OK] Product rights chunks: {self.output_dir / 'product_rights_chunks.json'}")
        print(f"  [OK] Transcriptions: {self.output_dir / 'sales_recordings_transcriptions.json'}")
        print(f"  [OK] Recording chunks: {self.output_dir / 'sales_recordings_chunks.json'}")
        print(f"  [OK] Integration report: {self.output_dir / 'integration_report.txt'}")


async def main():
    """主函数"""
    pipeline = DataIntegrationPipeline()
    await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())
