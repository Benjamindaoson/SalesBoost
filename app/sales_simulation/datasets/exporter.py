"""
数据集导出器
导出训练数据为标准格式
"""
import logging
import json
from pathlib import Path
from typing import List

from app.sales_simulation.schemas.preference import PreferencePair, SFTSample

logger = logging.getLogger(__name__)


class DatasetExporter:
    """数据集导出器"""
    
    @staticmethod
    def export_preference_pairs(
        pairs: List[PreferencePair],
        output_path: str,
    ) -> None:
        """
        导出偏好对为 JSONL 格式
        
        Args:
            pairs: 偏好对列表
            output_path: 输出路径
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for pair in pairs:
                line = json.dumps(pair.model_dump(), ensure_ascii=False)
                f.write(line + '\n')
        
        logger.info(f"Exported {len(pairs)} preference pairs to {output_path}")
    
    @staticmethod
    def export_sft_samples(
        samples: List[SFTSample],
        output_path: str,
    ) -> None:
        """
        导出 SFT 样本为 JSONL 格式
        
        Args:
            samples: SFT 样本列表
            output_path: 输出路径
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for sample in samples:
                line = json.dumps(sample.model_dump(), ensure_ascii=False)
                f.write(line + '\n')
        
        logger.info(f"Exported {len(samples)} SFT samples to {output_path}")




