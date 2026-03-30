"""
种子数据常量 - Mock 数据统一存放

供 API 在无 DB 或空表时使用，避免在 endpoint 中硬编码 Mock。
"""
from typing import Any, Dict, List

# ==================== 客户画像 ====================
SEED_CUSTOMER_PERSONAS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "张总",
        "role": "CEO",
        "company": "科技创新公司",
        "industry": "互联网",
        "pain_points": ["成本控制", "团队管理", "市场竞争"],
        "personality": "果断、注重效率",
        "difficulty": 3,
        "avatar_url": None,
    },
    {
        "id": 2,
        "name": "李经理",
        "role": "采购经理",
        "company": "制造企业",
        "industry": "制造业",
        "pain_points": ["供应链稳定", "价格谈判", "质量保证"],
        "personality": "谨慎、重视细节",
        "difficulty": 2,
        "avatar_url": None,
    },
    {
        "id": 3,
        "name": "王主管",
        "role": "IT主管",
        "company": "金融机构",
        "industry": "金融",
        "pain_points": ["系统安全", "合规要求", "技术升级"],
        "personality": "专业、严谨",
        "difficulty": 3,
        "avatar_url": None,
    },
]


def get_seed_customer_personas() -> List[Dict[str, Any]]:
    """返回种子客户画像"""
    return list(SEED_CUSTOMER_PERSONAS)
