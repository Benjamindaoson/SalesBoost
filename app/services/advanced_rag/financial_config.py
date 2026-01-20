"""
金融场景优化配置
针对信用卡销售场景的特殊配置和优化
"""
from typing import Dict, List, Any

# 金融关键词权重（用于BM25和查询扩展）
FINANCIAL_KEYWORDS = {
    "high_priority": [
        # 费率相关
        "年费", "费率", "利率", "手续费", "服务费",
        # 额度相关
        "额度", "信用额度", "可用额度", "临时额度",
        # 权益相关
        "权益", "优惠", "积分", "返现", "折扣",
        # 风险相关
        "风险", "合规", "条款", "规定", "限制",
    ],
    "medium_priority": [
        "产品", "功能", "申请", "办理", "激活",
        "还款", "账单", "分期", "最低还款",
    ],
}

# 金融实体类型（用于元数据过滤）
FINANCIAL_ENTITY_TYPES = {
    "product": ["信用卡", "借记卡", "理财", "基金", "保险"],
    "rate": ["年费", "费率", "利率", "手续费"],
    "limit": ["额度", "限额", "上限"],
    "benefit": ["权益", "优惠", "积分", "返现"],
}

# 销售阶段到内容类型的映射
STAGE_TO_CONTENT_TYPE = {
    "OPENING": ["script", "faq"],  # 开场：话术和FAQ
    "NEEDS_DISCOVERY": ["script", "strategy"],  # 需求挖掘：话术和策略
    "PRODUCT_INTRO": ["script", "case"],  # 产品介绍：话术和案例
    "OBJECTION_HANDLING": ["strategy", "case"],  # 异议处理：策略和案例
    "CLOSING": ["script", "strategy"],  # 成交：话术和策略
}

# 查询类型到检索策略的映射
QUERY_TYPE_TO_STRATEGY = {
    "factual": {
        "use_rag_fusion": False,
        "use_multi_vector": False,
        "top_k": 3,
        "min_relevance": 0.7,  # 高阈值
    },
    "exploratory": {
        "use_rag_fusion": False,
        "use_multi_vector": False,
        "top_k": 5,
        "min_relevance": 0.5,
    },
    "comparative": {
        "use_rag_fusion": False,
        "use_multi_vector": True,  # 需要多文档
        "top_k": 5,
        "min_relevance": 0.6,
    },
    "objection": {
        "use_rag_fusion": True,  # 异议处理需要最高准确率
        "use_multi_vector": False,
        "top_k": 3,
        "min_relevance": 0.6,
        "use_compression": True,  # 压缩以减少token
    },
    "procedural": {
        "use_rag_fusion": False,
        "use_multi_vector": False,
        "top_k": 5,
        "min_relevance": 0.5,
    },
}

# 金融场景的查询扩展模板
FINANCIAL_QUERY_EXPANSION_TEMPLATES = {
    "rate_query": [
        "{query} 费率是多少",
        "{query} 年费政策",
        "{query} 费用说明",
    ],
    "benefit_query": [
        "{query} 有什么权益",
        "{query} 优惠活动",
        "{query} 积分政策",
    ],
    "objection_query": [
        "如何应对 {query}",
        "{query} 的处理方法",
        "客户 {query} 怎么回复",
    ],
}

# 元数据过滤增强（金融场景）
FINANCIAL_METADATA_FILTERS = {
    "product_intro": {
        "type": {"$in": ["script", "case"]},
        "tags": {"$contains": "产品介绍"},
    },
    "objection_handling": {
        "type": {"$in": ["strategy", "case"]},
        "tags": {"$contains": "异议处理"},
    },
    "closing": {
        "type": {"$in": ["script", "strategy"]},
        "tags": {"$contains": "成交"},
    },
}

def get_financial_optimized_config() -> Dict[str, Any]:
    """获取金融场景优化配置"""
    return {
        "enable_hybrid": True,
        "enable_reranker": True,
        "enable_query_expansion": True,
        "enable_rag_fusion": False,  # 默认关闭，按需启用
        "enable_adaptive": True,  # 启用自适应检索
        "enable_multi_vector": False,  # 默认关闭
        "enable_context_compression": False,  # 默认关闭
        "enable_caching": True,
        "financial_optimized": True,
        "bm25_weight": 0.3,  # BM25权重
        "vector_weight": 0.7,  # 向量权重
        "rrf_k": 60,  # RRF常数
    }


