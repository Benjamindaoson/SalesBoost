"""
GraphRAG 模块 - 知识图谱增强的 RAG 系统

核心组件：
- graph_schema: 销售场景知识图谱 Schema 定义
- relation_extractor: 从文档中提取实体关系三元组
- graph_builder: 知识图谱构建与管理
- community_detector: 社区检测与摘要生成
- graph_retriever: 基于图的检索
- explainability: 可解释性模块，提供推理路径
"""

from app.services.graph_rag.graph_schema import (
    EntityType,
    RelationType,
    Entity,
    Relation,
    Triple,
    SubGraph,
    CommunitySummary,
    GraphRAGResult,
)
from app.services.graph_rag.graph_builder import SalesKnowledgeGraph
from app.services.graph_rag.relation_extractor import RelationExtractor
from app.services.graph_rag.community_detector import CommunityDetector
from app.services.graph_rag.graph_retriever import GraphRetriever
from app.services.graph_rag.explainability import (
    ExplainabilityModule,
    ExplainableResult,
    ReasoningPath,
    ReasoningStep,
)

__all__ = [
    # Schema
    "EntityType",
    "RelationType",
    "Entity",
    "Relation",
    "Triple",
    "SubGraph",
    "CommunitySummary",
    "GraphRAGResult",
    # Core classes
    "SalesKnowledgeGraph",
    "RelationExtractor",
    "CommunityDetector",
    "GraphRetriever",
    # Explainability
    "ExplainabilityModule",
    "ExplainableResult",
    "ReasoningPath",
    "ReasoningStep",
]

