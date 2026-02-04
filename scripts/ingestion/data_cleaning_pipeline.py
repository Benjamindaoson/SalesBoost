#!/usr/bin/env python3
"""
数据清洗脚本 - 产品权益表格 + 销售录音
Data Cleaning Script for Product Rights & Sales Recordings

Author: Claude Sonnet 4.5
Date: 2026-02-01
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import pandas as pd
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class DataCleaningPipeline:
    """数据清洗管道"""

    def __init__(self):
        self.source_dir = Path("销冠能力复制数据库")
        self.product_rights_dir = self.source_dir / "产品权益"
        self.sales_recordings_dir = self.source_dir / "销售录音"

        # 创建输出目录
        timestamp = datetime.now().strftime("%Y%m%d")
        batch_num = "001"
        self.output_dir = self.source_dir / f"cleaned_data_{timestamp}_{batch_num}"
        self.output_product_dir = self.output_dir / "product_rights"
        self.output_recordings_dir = self.output_dir / "sales_recordings"

        # 创建目录
        self.output_dir.mkdir(exist_ok=True)
        self.output_product_dir.mkdir(exist_ok=True)
        self.output_recordings_dir.mkdir(exist_ok=True)

        # 统计数据
        self.stats = {
            "product_rights": {
                "original_files": 0,
                "cleaned_files": 0,
                "total_rows_before": 0,
                "total_rows_after": 0,
                "duplicates_removed": 0,
                "nulls_removed": 0,
                "errors": []
            },
            "sales_recordings": {
                "original_files": 0,
                "cleaned_files": 0,
                "total_size_before_mb": 0,
                "total_size_after_mb": 0,
                "format_conversions": 0,
                "errors": []
            }
        }

    def clean_excel_file(self, file_path: Path) -> Dict[str, Any]:
        """清洗单个 Excel 文件"""
        try:
            print(f"\n处理表格: {file_path.name}")

            # 读取 Excel
            df = pd.read_excel(file_path)
            original_rows = len(df)

            print(f"  原始行数: {original_rows}")
            print(f"  原始列数: {len(df.columns)}")

            # 1. 去除完全空白的行
            df = df.dropna(how='all')
            after_null_removal = len(df)
            nulls_removed = original_rows - after_null_removal

            # 2. 去除重复行
            df = df.drop_duplicates()
            after_dedup = len(df)
            duplicates_removed = after_null_removal - after_dedup

            # 3. 标准化列名（去除空格、统一小写）
            df.columns = df.columns.str.strip()

            # 4. 去除列中的前后空格
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].str.strip() if df[col].dtype == 'object' else df[col]

            # 5. 保存清洗后的文件
            output_file = self.output_product_dir / file_path.name

            # 保存为 Excel 和 CSV 两种格式
            df.to_excel(output_file, index=False, engine='openpyxl')
            csv_file = output_file.with_suffix('.csv')
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')

            print(f"  [OK] 清洗后行数: {after_dedup}")
            print(f"  [OK] 去除空行: {nulls_removed}")
            print(f"  [OK] 去除重复: {duplicates_removed}")
            print(f"  [OK] 保存到: {output_file.name}")

            return {
                "success": True,
                "file": file_path.name,
                "original_rows": original_rows,
                "cleaned_rows": after_dedup,
                "nulls_removed": nulls_removed,
                "duplicates_removed": duplicates_removed,
                "error_rate": 0.0
            }

        except Exception as e:
            print(f"  ✗ 错误: {e}")
            return {
                "success": False,
                "file": file_path.name,
                "error": str(e)
            }

    def clean_product_rights_data(self):
        """清洗产品权益表格数据"""
        print("\n" + "="*70)
        print("清洗产品权益表格数据")
        print("="*70)

        # 查找所有 Excel 文件
        excel_files = list(self.product_rights_dir.glob("*.xlsx")) + \
                     list(self.product_rights_dir.glob("*.xls"))

        self.stats["product_rights"]["original_files"] = len(excel_files)

        results = []

        for file_path in tqdm(excel_files, desc="处理表格文件"):
            result = self.clean_excel_file(file_path)
            results.append(result)

            if result["success"]:
                self.stats["product_rights"]["cleaned_files"] += 1
                self.stats["product_rights"]["total_rows_before"] += result["original_rows"]
                self.stats["product_rights"]["total_rows_after"] += result["cleaned_rows"]
                self.stats["product_rights"]["duplicates_removed"] += result["duplicates_removed"]
                self.stats["product_rights"]["nulls_removed"] += result["nulls_removed"]
            else:
                self.stats["product_rights"]["errors"].append(result)

        return results

    def process_audio_file(self, file_path: Path) -> Dict[str, Any]:
        """处理单个音频文件"""
        try:
            print(f"\n处理音频: {file_path.name}")

            # 获取文件大小
            original_size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"  原始大小: {original_size_mb:.2f} MB")
            print(f"  原始格式: {file_path.suffix}")

            # 标准化文件名
            # 去除特殊字符，统一命名格式
            clean_name = file_path.stem
            clean_name = clean_name.replace(" ", "_").replace("-", "_")

            # 如果是 WAV 格式，需要转换为 MP3
            if file_path.suffix.lower() == '.wav':
                output_file = self.output_recordings_dir / f"{clean_name}.mp3"

                # 使用 pydub 转换（需要 ffmpeg）
                try:
                    from pydub import AudioSegment
                    from pydub.silence import detect_nonsilent

                    # 加载音频
                    audio = AudioSegment.from_wav(file_path)

                    # 去除超过3秒的静音片段
                    nonsilent_ranges = detect_nonsilent(
                        audio,
                        min_silence_len=3000,  # 3秒
                        silence_thresh=-40
                    )

                    if nonsilent_ranges:
                        # 合并非静音片段
                        processed_audio = AudioSegment.empty()
                        for start, end in nonsilent_ranges:
                            processed_audio += audio[start:end]
                    else:
                        processed_audio = audio

                    # 导出为 MP3，采样率 44.1kHz
                    processed_audio.export(
                        output_file,
                        format="mp3",
                        bitrate="192k",
                        parameters=["-ar", "44100"]
                    )

                    converted = True

                except ImportError:
                    # 如果没有 pydub，直接复制
                    print("  ⚠ pydub 未安装，直接复制文件")
                    output_file = self.output_recordings_dir / file_path.name
                    shutil.copy2(file_path, output_file)
                    converted = False

            else:
                # MP3 文件直接复制
                output_file = self.output_recordings_dir / f"{clean_name}.mp3"
                shutil.copy2(file_path, output_file)
                converted = False

            # 获取输出文件大小
            output_size_mb = output_file.stat().st_size / (1024 * 1024)

            print(f"  [OK] 处理后大小: {output_size_mb:.2f} MB")
            print(f"  [OK] 保存到: {output_file.name}")

            return {
                "success": True,
                "file": file_path.name,
                "original_size_mb": original_size_mb,
                "cleaned_size_mb": output_size_mb,
                "converted": converted,
                "output_file": output_file.name
            }

        except Exception as e:
            print(f"  ✗ 错误: {e}")
            return {
                "success": False,
                "file": file_path.name,
                "error": str(e)
            }

    def clean_sales_recordings(self):
        """清洗销售录音数据"""
        print("\n" + "="*70)
        print("清洗销售录音数据")
        print("="*70)

        # 查找所有音频文件
        audio_files = list(self.sales_recordings_dir.glob("*.mp3")) + \
                     list(self.sales_recordings_dir.glob("*.wav")) + \
                     list(self.sales_recordings_dir.glob("*.m4a"))

        self.stats["sales_recordings"]["original_files"] = len(audio_files)

        results = []

        for file_path in tqdm(audio_files, desc="处理音频文件"):
            result = self.process_audio_file(file_path)
            results.append(result)

            if result["success"]:
                self.stats["sales_recordings"]["cleaned_files"] += 1
                self.stats["sales_recordings"]["total_size_before_mb"] += result["original_size_mb"]
                self.stats["sales_recordings"]["total_size_after_mb"] += result["cleaned_size_mb"]
                if result.get("converted"):
                    self.stats["sales_recordings"]["format_conversions"] += 1
            else:
                self.stats["sales_recordings"]["errors"].append(result)

        return results

    def generate_report(self):
        """生成数据处理报告"""
        print("\n" + "="*70)
        print("生成数据处理报告")
        print("="*70)

        report = {
            "processing_date": datetime.now().isoformat(),
            "output_directory": str(self.output_dir),
            "product_rights": self.stats["product_rights"],
            "sales_recordings": self.stats["sales_recordings"]
        }

        # 保存 JSON 报告
        report_file = self.output_dir / "data_cleaning_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 生成可读的文本报告
        text_report = self.output_dir / "data_cleaning_report.txt"
        with open(text_report, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("数据清洗报告 - Data Cleaning Report\n")
            f.write("="*70 + "\n\n")
            f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"输出目录: {self.output_dir}\n\n")

            f.write("="*70 + "\n")
            f.write("产品权益表格数据 - Product Rights Data\n")
            f.write("="*70 + "\n")
            pr = self.stats["product_rights"]
            f.write(f"原始文件数: {pr['original_files']}\n")
            f.write(f"清洗后文件数: {pr['cleaned_files']}\n")
            f.write(f"原始总行数: {pr['total_rows_before']}\n")
            f.write(f"清洗后总行数: {pr['total_rows_after']}\n")
            f.write(f"去除空行: {pr['nulls_removed']}\n")
            f.write(f"去除重复行: {pr['duplicates_removed']}\n")

            if pr['total_rows_before'] > 0:
                error_rate = (pr['nulls_removed'] + pr['duplicates_removed']) / pr['total_rows_before'] * 100
                f.write(f"数据清洗率: {error_rate:.2f}%\n")
                f.write(f"数据保留率: {100 - error_rate:.2f}%\n")

            f.write(f"\n错误数: {len(pr['errors'])}\n")

            f.write("\n" + "="*70 + "\n")
            f.write("销售录音数据 - Sales Recordings Data\n")
            f.write("="*70 + "\n")
            sr = self.stats["sales_recordings"]
            f.write(f"原始文件数: {sr['original_files']}\n")
            f.write(f"处理后文件数: {sr['cleaned_files']}\n")
            f.write(f"原始总大小: {sr['total_size_before_mb']:.2f} MB\n")
            f.write(f"处理后总大小: {sr['total_size_after_mb']:.2f} MB\n")
            f.write(f"格式转换数: {sr['format_conversions']}\n")
            f.write(f"错误数: {len(sr['errors'])}\n")

            f.write("\n" + "="*70 + "\n")
            f.write("质量控制 - Quality Control\n")
            f.write("="*70 + "\n")

            if pr['total_rows_before'] > 0:
                actual_error_rate = (pr['nulls_removed'] + pr['duplicates_removed']) / pr['total_rows_before']
                f.write(f"表格数据错误率: {actual_error_rate:.4f} ({actual_error_rate * 100:.2f}%)\n")
                f.write(f"质量标准: < 0.1% ({'[OK] 通过' if actual_error_rate < 0.001 else '[ERROR] 未通过'})\n")

            f.write(f"\n音频文件完整性: {sr['cleaned_files']}/{sr['original_files']} ")
            f.write(f"({'[OK] 通过' if sr['cleaned_files'] == sr['original_files'] else '[ERROR] 未通过'})\n")

        print("\n[OK] 报告已保存:")
        print(f"  - JSON: {report_file}")
        print(f"  - TXT: {text_report}")

        return report

    def run(self):
        """运行完整的数据清洗流程"""
        print("\n" + "="*70)
        print("数据清洗管道启动 - Data Cleaning Pipeline")
        print("="*70)
        print(f"输出目录: {self.output_dir}")
        print()

        # 1. 清洗产品权益数据
        self.clean_product_rights_data()

        # 2. 清洗销售录音数据
        self.clean_sales_recordings()

        # 3. 生成报告
        self.generate_report()

        # 4. 打印摘要
        print("\n" + "="*70)
        print("数据清洗完成 - Data Cleaning Complete")
        print("="*70)
        print("\n产品权益表格:")
        print(f"  [OK] 处理文件: {self.stats['product_rights']['cleaned_files']}/{self.stats['product_rights']['original_files']}")
        print(f"  [OK] 数据行数: {self.stats['product_rights']['total_rows_after']} (原始: {self.stats['product_rights']['total_rows_before']})")

        print("\n销售录音:")
        print(f"  [OK] 处理文件: {self.stats['sales_recordings']['cleaned_files']}/{self.stats['sales_recordings']['original_files']}")
        print(f"  [OK] 总大小: {self.stats['sales_recordings']['total_size_after_mb']:.2f} MB")

        print(f"\n输出位置: {self.output_dir}")
        print("\n交付物:")
        print(f"  [OK] 清洗后的表格数据: {self.output_product_dir}")
        print(f"  [OK] 处理后的音频文件: {self.output_recordings_dir}")
        print(f"  [OK] 数据处理报告: {self.output_dir / 'data_cleaning_report.txt'}")
        print(f"  [OK] 数据处理日志: {self.output_dir / 'data_cleaning_report.json'}")


def main():
    """主函数"""
    pipeline = DataCleaningPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
