"""
可解释性模块 - 提供 GraphRAG 检索结果的推理路径和解释

为检索结果提供可解释性，帮助用户理解为什么返回这些结果。
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from app.services.graph_rag.graph_schema import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    SubGraph,
    GraphRAGResult,
)
from app.services.graph_rag.graph_builder import SalesKnowledgeGraph

logger = logging.getLogger(__name__)


@dataclass
class ReasoningStep:
    """推理步骤"""
    step_number: int
    from_entity: str
    relation: str
    to_entity: str
    explanation: str
    confidence: float = 1.0


@dataclass
class ReasoningPath:
    """推理路径"""
    path_id: str
    steps: List[ReasoningStep] = field(default_factory=list)
    total_confidence: float = 1.0
    summary: str = ""
    
    def to_text(self) -> str:
        """转换为文本描述"""
        if not self.steps:
            return ""
        
        lines = [f"推理路径 {self.path_id}:"]
        for step in self.steps:
            lines.append(f"  {step.step_number}. {step.from_entity} --[{step.relation}]--> {step.to_entity}")
            if step.explanation:
                lines.append(f"     说明: {step.explanation}")
        
        if self.summary:
            lines.append(f"  结论: {self.summary}")
        
        return "\n".join(lines)


@dataclass
class ExplainableResult:
    """可解释的检索结果"""
    content: str
    source_type: str
    relevance_score: float
    reasoning_paths: List[ReasoningPath] = field(default_factory=list)
    key_entities: List[str] = field(default_factory=list)
    explanation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "source_type": self.source_type,
            "relevance_score": self.relevance_score,
            "reasoning_paths": [
                {
                    "path_id": p.path_id,
                    "steps": [
                        {
                            "from": s.from_entity,
                            "relation": s.relation,
                            "to": s.to_entity,
                            "explanation": s.explanation,
                        }
                        for s in p.steps
                    ],
                    "summary": p.summary,
                }
                for p in self.reasoning_paths
            ],
            "key_entities": self.key_entities,
            "explanation": self.explanation,
        }


# 关系类型的中文解释
RELATION_EXPLANATIONS = {
    RelationType.HAS_FEATURE: "具有特性",
    RelationType.PROVIDES_BENEFIT: "提供利益",
    RelationType.ADDRESSES: "应对/解决",
    RelationType.LEADS_TO: "可能导致",
    RelationType.APPLIES_TO_STAGE: "适用于阶段",
    RelationType.SUITS_CUSTOMER: "适合客户类型",
    RelationType.SIMILAR_TO: "相似于",
    RelationType.COUNTERS: "可反驳",
    RelationType.VARIANT_OF: "是变体",
    RelationType.USES_KEYWORD: "使用关键词",
    RelationType.EXTRACTED_FROM: "提取自",
    RelationType.MENTIONED_IN: "提及于",
    RelationType.FOLLOWS: "后续是",
    RelationType.COMPETES_WITH: "竞争于",
    RelationType.APPLICABLE_IN: "适用于场景",
    RelationType.TRIGGERS: "触发",
}


class ExplainabilityModule:
    """
    可解释性模块
    
    功能：
    - 生成推理路径解释
    - 为检索结果提供上下文说明
    - 高亮关键实体和关系
    """
    
    def __init__(self, knowledge_graph: SalesKnowledgeGraph):
        """
        初始化可解释性模块
        
        Args:
            knowledge_graph: 知识图谱实例
        """
        self.kg = knowledge_graph
    
    def explain_subgraph(
        self,
        subgraph: SubGraph,
        query_entities: List[str],
    ) -> List[ReasoningPath]:
        """
        解释子图检索结果
        
        Args:
            subgraph: 检索到的子图
            query_entities: 查询实体
            
        Returns:
            推理路径列表
        """
        paths = []
        
        # 找到查询实体在子图中的位置
        query_entity_ids = set()
        for name in query_entities:
            entity = self.kg.get_entity_by_name(name)
            if entity:
                query_entity_ids.add(entity.id)
        
        # 找到目标实体（Response, Script 类型）
        target_entities = [
            e for e in subgraph.entities
            if e.type in [EntityType.RESPONSE, EntityType.SCRIPT]
        ]
        
        # 为每个目标实体生成推理路径
        for i, target in enumerate(target_entities[:5]):  # 限制数量
            for query_id in query_entity_ids:
                path = self._build_reasoning_path(
                    subgraph,
                    query_id,
                    target.id,
                    path_id=f"path_{i+1}",
                )
                if path and path.steps:
                    paths.append(path)
                    break  # 每个目标只需要一条路径
        
        return paths
    
    def _build_reasoning_path(
        self,
        subgraph: SubGraph,
        start_id: str,
        end_id: str,
        path_id: str,
    ) -> Optional[ReasoningPath]:
        """
        构建从起点到终点的推理路径
        
        Args:
            subgraph: 子图
            start_id: 起始实体ID
            end_id: 目标实体ID
            path_id: 路径ID
            
        Returns:
            推理路径
        """
        # 使用 BFS 在子图中查找路径
        from collections import deque
        
        # 构建邻接表
        adjacency: Dict[str, List[Tuple[str, Relation]]] = {}
        for rel in subgraph.relations:
            if rel.source_id not in adjacency:
                adjacency[rel.source_id] = []
            adjacency[rel.source_id].append((rel.target_id, rel))
            
            # 无向处理
            if rel.target_id not in adjacency:
                adjacency[rel.target_id] = []
            adjacency[rel.target_id].append((rel.source_id, rel))
        
        # BFS
        queue = deque([(start_id, [])])
        visited = {start_id}
        
        while queue:
            current_id, path = queue.popleft()
            
            if current_id == end_id:
                # 找到路径，构建 ReasoningPath
                return self._create_reasoning_path(path, path_id, subgraph)
            
            for neighbor_id, relation in adjacency.get(current_id, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [(current_id, relation, neighbor_id)]))
        
        return None
    
    def _create_reasoning_path(
        self,
        path_edges: List[Tuple[str, Relation, str]],
        path_id: str,
        subgraph: SubGraph,
    ) -> ReasoningPath:
        """
        从边列表创建推理路径
        
        Args:
            path_edges: 边列表 [(from_id, relation, to_id), ...]
            path_id: 路径ID
            subgraph: 子图
            
        Returns:
            推理路径
        """
        steps = []
        total_confidence = 1.0
        
        entity_map = {e.id: e for e in subgraph.entities}
        
        for i, (from_id, relation, to_id) in enumerate(path_edges):
            from_entity = entity_map.get(from_id)
            to_entity = entity_map.get(to_id)
            
            if not from_entity or not to_entity:
                continue
            
            # 获取关系解释
            rel_type = relation.type if isinstance(relation.type, RelationType) else RelationType(relation.type)
            explanation = RELATION_EXPLANATIONS.get(rel_type, str(rel_type))
            
            step = ReasoningStep(
                step_number=i + 1,
                from_entity=from_entity.name,
                relation=explanation,
                to_entity=to_entity.name,
                explanation=self._generate_step_explanation(from_entity, rel_type, to_entity),
                confidence=relation.confidence,
            )
            steps.append(step)
            total_confidence *= relation.confidence
        
        # 生成路径摘要
        summary = self._generate_path_summary(steps)
        
        return ReasoningPath(
            path_id=path_id,
            steps=steps,
            total_confidence=total_confidence,
            summary=summary,
        )
    
    def _generate_step_explanation(
        self,
        from_entity: Entity,
        relation: RelationType,
        to_entity: Entity,
    ) -> str:
        """生成单步推理的解释"""
        templates = {
            RelationType.ADDRESSES: f"「{from_entity.name}」可以用来应对「{to_entity.name}」这类异议",
            RelationType.PROVIDES_BENEFIT: f"「{from_entity.name}」能为客户带来「{to_entity.name}」",
            RelationType.HAS_FEATURE: f"「{from_entity.name}」具有「{to_entity.name}」特性",
            RelationType.APPLIES_TO_STAGE: f"「{from_entity.name}」适用于「{to_entity.name}」阶段",
            RelationType.SUITS_CUSTOMER: f"「{from_entity.name}」适合「{to_entity.name}」类型的客户",
            RelationType.SIMILAR_TO: f"「{from_entity.name}」与「{to_entity.name}」相似",
            RelationType.COUNTERS: f"「{from_entity.name}」可以反驳「{to_entity.name}」",
            RelationType.LEADS_TO: f"「{from_entity.name}」可能引发「{to_entity.name}」",
        }
        
        return templates.get(relation, f"「{from_entity.name}」与「{to_entity.name}」相关")
    
    def _generate_path_summary(self, steps: List[ReasoningStep]) -> str:
        """生成路径摘要"""
        if not steps:
            return ""
        
        first_entity = steps[0].from_entity
        last_entity = steps[-1].to_entity
        
        return f"从「{first_entity}」经过 {len(steps)} 步推理到达「{last_entity}」"
    
    def explain_result(
        self,
        result: GraphRAGResult,
        query: str,
    ) -> List[ExplainableResult]:
        """
        为 GraphRAG 结果生成解释
        
        Args:
            result: GraphRAG 检索结果
            query: 原始查询
            
        Returns:
            可解释的结果列表
        """
        explainable_results = []
        
        # 提取查询实体
        query_entities = self._extract_entities_from_query(query)
        
        # 处理子图结果
        for subgraph in result.local_subgraphs:
            # 生成推理路径
            paths = self.explain_subgraph(subgraph, query_entities)
            
            # 为每个目标实体创建可解释结果
            for entity in subgraph.entities:
                if entity.type in [EntityType.RESPONSE, EntityType.SCRIPT]:
                    # 找到指向该实体的路径
                    relevant_paths = [
                        p for p in paths
                        if p.steps and p.steps[-1].to_entity == entity.name
                    ]
                    
                    explainable_results.append(ExplainableResult(
                        content=entity.name,
                        source_type="knowledge_graph",
                        relevance_score=subgraph.relevance_score,
                        reasoning_paths=relevant_paths,
                        key_entities=[entity.name] + [
                            s.from_entity for p in relevant_paths for s in p.steps
                        ],
                        explanation=self._generate_result_explanation(entity, relevant_paths),
                    ))
        
        # 处理社区摘要结果
        for summary in result.community_summaries:
            explainable_results.append(ExplainableResult(
                content=summary.summary,
                source_type="community_summary",
                relevance_score=summary.relevance_score,
                reasoning_paths=[],
                key_entities=summary.key_entities,
                explanation=f"来自知识社区「{summary.title}」的摘要，包含 {summary.size} 个相关知识点",
            ))
        
        return explainable_results
    
    def _extract_entities_from_query(self, query: str) -> List[str]:
        """从查询中提取实体名称"""
        entities = []
        query_lower = query.lower()
        
        for entity_name in self.kg.name_to_id.keys():
            if entity_name.lower() in query_lower:
                entities.append(entity_name)
        
        return entities
    
    def _generate_result_explanation(
        self,
        entity: Entity,
        paths: List[ReasoningPath],
    ) -> str:
        """生成结果解释"""
        if not paths:
            return f"「{entity.name}」是相关的{self._get_entity_type_name(entity.type)}"
        
        # 使用第一条路径生成解释
        path = paths[0]
        if path.steps:
            first_step = path.steps[0]
            return f"基于「{first_step.from_entity}」，通过 {len(path.steps)} 步推理找到「{entity.name}」"
        
        return f"「{entity.name}」与查询相关"
    
    def _get_entity_type_name(self, entity_type: EntityType) -> str:
        """获取实体类型的中文名称"""
        type_names = {
            EntityType.PRODUCT: "产品",
            EntityType.FEATURE: "特性",
            EntityType.BENEFIT: "利益点",
            EntityType.OBJECTION: "异议",
            EntityType.RESPONSE: "应对话术",
            EntityType.SALES_STAGE: "销售阶段",
            EntityType.CUSTOMER_TYPE: "客户类型",
            EntityType.SCRIPT: "话术模板",
            EntityType.SCENARIO: "场景",
            EntityType.KEYWORD: "关键词",
            EntityType.DOCUMENT: "文档",
        }
        return type_names.get(entity_type, "知识点")
    
    def generate_explanation_text(
        self,
        result: GraphRAGResult,
        query: str,
        max_paths: int = 3,
    ) -> str:
        """
        生成人类可读的解释文本
        
        Args:
            result: GraphRAG 检索结果
            query: 原始查询
            max_paths: 最大显示路径数
            
        Returns:
            解释文本
        """
        lines = [f"【检索解释】"]
        lines.append(f"查询：{query}")
        lines.append("")
        
        # 推理路径
        if result.reasoning_paths:
            lines.append("【推理路径】")
            for i, path in enumerate(result.reasoning_paths[:max_paths]):
                lines.append(f"路径 {i+1}: {' -> '.join(path)}")
            lines.append("")
        
        # 相关实体
        if result.local_subgraphs:
            lines.append("【相关知识】")
            for subgraph in result.local_subgraphs[:2]:
                for entity in subgraph.entities[:5]:
                    lines.append(f"- {entity.name} ({self._get_entity_type_name(entity.type)})")
            lines.append("")
        
        # 社区摘要
        if result.community_summaries:
            lines.append("【知识社区】")
            for summary in result.community_summaries[:2]:
                lines.append(f"- {summary.title}: {summary.summary[:100]}...")
        
        return "\n".join(lines)

