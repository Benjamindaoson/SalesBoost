"""
数据集 API 端点
"""
import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def list_datasets():
    """列出所有可用数据集"""
    return {
        "datasets": [
            {"id": "preference_pairs_001", "type": "dpo", "size": 150},
            {"id": "sft_samples_001", "type": "sft", "size": 500},
        ],
        "count": 2,
    }


@router.get("/{dataset_id}/download")
async def download_dataset(dataset_id: str):
    """
    下载数据集
    
    Args:
        dataset_id: 数据集 ID
        
    Returns:
        数据集文件
    """
    # 简化版：返回示例数据
    return {
        "dataset_id": dataset_id,
        "download_url": f"/api/v1/sales-sim/datasets/{dataset_id}/file",
        "format": "jsonl",
    }




