"""
图检索器 - 基于知识图谱的检索

支持局部子图检索、全局社区检索和多跳推理。
"""
import logging
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict

from app.services.graph_rag.graph_schema import (
    Entity,
    EntityType,
    RelationType,
    SubGraph,
    CommunitySummary,
    GraphRAGResult,
)
from app.services.graph_rag.graph_builder import SalesKnowledgeGraph
from app.services.graph_rag.community_detector import CommunityDetector

logger = logging.getLogger(__name__)


class GraphRetriever:
    """
    图检索器
    
    功能：
    - 局部检索：基于查询实体的子图检索
    - 全局检索：基于社区摘要的全局检索
    - 混合检索：结合局部和全局的混合模式
    - 多跳推理：支持多跳路径发现
    """
    
    def __init__(
        self,
        knowledge_graph: SalesKnowledgeGraph,
        community_detector: Optional[CommunityDetector] = None,
        embedding_fn=None,
    ):
        """
        初始化图检索器
        
        Args:
            knowledge_graph: 知识图谱实例
            community_detector: 社区检测器实例
            embedding_fn: 嵌入函数 (List[str]) -> List[List[float]]
        """
        self.kg = knowledge_graph
        self.community_detector = community_detector
        self.embedding_fn = embedding_fn
        
        # 实体名称嵌入缓存
        self._entity_embeddings: Dict[str, List[float]] = {}
    
    async def retrieve_subgraph(
        self,
        query_entities: List[str],
        max_hops: int = 2,
        max_nodes: int = 20,
        relation_types: Optional[List[RelationType]] = None,
    ) -> SubGraph:
        """
        基于查询实体检索相关子图
        
        Args:
            query_entities: 查询实体名称列表
            max_hops: 最大跳数
            max_nodes: 最大节点数
            relation_types: 过滤的关系类型
            
        Returns:
            相关子图
        """
        start_time = time.time()
        
        # 将实体名称转换为ID
        entity_ids = []
        for name in query_entities:
            entity = self.kg.get_entity_by_name(name)
            if entity:
                entity_ids.append(entity.id)
            else:
                # 尝试模糊匹配
                matched_id = self._fuzzy_match_entity(name)
                if matched_id:
                    entity_ids.append(matched_id)
        
        if not entity_ids:
            logger.warning(f"No matching entities found for: {query_entities}")
            return SubGraph()
        
        # 获取子图
        subgraph = self.kg.get_subgraph(
            center_entity_ids=entity_ids,
            max_hops=max_hops,
            max_nodes=max_nodes,
            relation_types=relation_types,
        )
        
        # 计算相关性分数
        subgraph.relevance_score = self._calculate_subgraph_relevance(
            subgraph, entity_ids
        )
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Subgraph retrieval: {len(subgraph.entities)} entities, {len(subgraph.relations)} relations, {elapsed:.1f}ms")
        
        return subgraph
    
    async def retrieve_by_community(
        self,
        query: str,
        top_k: int = 3,
        level: int = 0,
    ) -> List[CommunitySummary]:
        """
        基于社区摘要的全局检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            level: 社区层级
            
        Returns:
            相关社区摘要列表
        """
        if not self.community_detector:
            logger.warning("Community detector not available")
            return []
        
        start_time = time.time()
        
        # 生成查询嵌入
        if self.embedding_fn:
            try:
                query_embedding = self.embedding_fn([query])
                if query_embedding:
                    summaries = self.community_detector.search_communities_by_embedding(
                        query_embedding[0], top_k, level
                    )
                    
                    elapsed = (time.time() - start_time) * 1000
                    logger.info(f"Community retrieval: {len(summaries)} communities, {elapsed:.1f}ms")
                    return summaries
            except Exception as e:
                logger.error(f"Embedding-based community search failed: {e}")
        
        # 降级：基于关键词匹配
        return self._keyword_match_communities(query, top_k, level)
    
    async def hybrid_search(
        self,
        query: str,
        query_entities: Optional[List[str]] = None,
        max_hops: int = 2,
        max_local_nodes: int = 20,
        top_k_communities: int = 3,
        community_level: int = 0,
    ) -> GraphRAGResult:
        """
        混合检索：结合局部子图和全局社区
        
        Args:
            query: 查询文本
            query_entities: 查询实体（可选，会自动提取）
            max_hops: 最大跳数
            max_local_nodes: 局部子图最大节点数
            top_k_communities: 返回的社区数量
            community_level: 社区层级
            
        Returns:
            GraphRAG 检索结果
        """
        start_time = time.time()
        
        # 1. 提取查询实体（如果未提供）
        if not query_entities:
            query_entities = await self._extract_query_entities(query)
        
        result = GraphRAGResult(
            query=query,
            mode="hybrid",
        )
        
        # 2. 局部子图检索
        if query_entities:
            subgraph = await self.retrieve_subgraph(
                query_entities=query_entities,
                max_hops=max_hops,
                max_nodes=max_local_nodes,
            )
            if subgraph.entities:
                result.local_subgraphs.append(subgraph)
                result.total_entities += len(subgraph.entities)
                result.total_relations += len(subgraph.relations)
        
        # 3. 全局社区检索
        community_summaries = await self.retrieve_by_community(
            query=query,
            top_k=top_k_communities,
            level=community_level,
        )
        result.community_summaries = community_summaries
        
        # 4. 发现推理路径
        if len(query_entities) >= 2:
            paths = self._find_reasoning_paths(query_entities[:2])
            result.reasoning_paths = paths
        
        # 5. 构建上下文
        result.build_context()
        
        result.retrieval_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Hybrid search completed: {result.total_entities} entities, "
            f"{len(result.community_summaries)} communities, {result.retrieval_time_ms:.1f}ms"
        )
        
        return result
    
    async def multi_hop_reasoning(
        self,
        start_entity: str,
        end_entity: str,
        max_hops: int = 4,
    ) -> List[List[Tuple[Entity, str, Entity]]]:
        """
        多跳推理：查找两个实体之间的推理路径
        
        Args:
            start_entity: 起始实体名称
            end_entity: 目标实体名称
            max_hops: 最大跳数
            
        Returns:
            推理路径列表，每条路径是 [(实体, 关系, 实体), ...] 的列表
        """
        # 获取实体ID
        start = self.kg.get_entity_by_name(start_entity)
        end = self.kg.get_entity_by_name(end_entity)
        
        if not start or not end:
            logger.warning(f"Entity not found: {start_entity} or {end_entity}")
            return []
        
        # 查找路径
        paths = self.kg.find_paths(start.id, end.id, max_hops)
        
        # 转换为详细路径
        detailed_paths = []
        for path in paths:
            detailed = []
            for i in range(len(path) - 1):
                source_entity = self.kg.get_entity(path[i])
                target_entity = self.kg.get_entity(path[i + 1])
                
                if not source_entity or not target_entity:
                    continue
                
                # 获取关系
                relation_type = "RELATED"
                if self.kg.graph.has_edge(path[i], path[i + 1]):
                    edge_data = self.kg.graph.edges[path[i], path[i + 1]]
                    relation_type = edge_data.get("type", "RELATED")
                elif self.kg.graph.has_edge(path[i + 1], path[i]):
                    edge_data = self.kg.graph.edges[path[i + 1], path[i]]
                    relation_type = edge_data.get("type", "RELATED")
                
                detailed.append((source_entity, relation_type, target_entity))
            
            if detailed:
                detailed_paths.append(detailed)
        
        return detailed_paths
    
    async def retrieve_for_objection(
        self,
        objection_text: str,
        sales_stage: Optional[str] = None,
        customer_type: Optional[str] = None,
        top_k: int = 5,
    ) -> SubGraph:
        """
        针对异议检索相关知识
        
        专门为异议处理场景优化的检索方法。
        
        Args:
            objection_text: 异议文本
            sales_stage: 销售阶段
            customer_type: 客户类型
            top_k: 返回数量
            
        Returns:
            包含异议应对策略的子图
        """
        # 1. 查找匹配的异议实体
        objection_entities = self.kg.get_entities_by_type(EntityType.OBJECTION)
        matched_objections = []
        
        objection_lower = objection_text.lower()
        for entity in objection_entities:
            # 简单的文本匹配
            if entity.name.lower() in objection_lower or objection_lower in entity.name.lower():
                matched_objections.append(entity)
            # 关键词匹配
            elif any(kw in objection_lower for kw in entity.properties.get("keywords", [])):
                matched_objections.append(entity)
        
        if not matched_objections:
            # 尝试使用嵌入相似度
            matched_objections = await self._find_similar_entities(
                objection_text, EntityType.OBJECTION, top_k=3
            )
        
        if not matched_objections:
            logger.warning(f"No matching objections found for: {objection_text}")
            return SubGraph()
        
        # 2. 获取异议相关的子图
        entity_ids = [e.id for e in matched_objections]
        
        # 优先获取 ADDRESSES 关系（应对话术）
        subgraph = self.kg.get_subgraph(
            center_entity_ids=entity_ids,
            max_hops=2,
            max_nodes=top_k * 3,
            relation_types=[
                RelationType.ADDRESSES,
                RelationType.COUNTERS,
                RelationType.SIMILAR_TO,
            ],
        )
        
        # 3. 根据阶段和客户类型过滤
        if sales_stage or customer_type:
            subgraph = self._filter_subgraph_by_context(
                subgraph, sales_stage, customer_type
            )
        
        return subgraph
    
    def _fuzzy_match_entity(self, name: str) -> Optional[str]:
        """模糊匹配实体名称"""
        name_lower = name.lower()
        
        best_match = None
        best_score = 0
        
        for entity_name, entity_id in self.kg.name_to_id.items():
            entity_lower = entity_name.lower()
            
            # 完全包含
            if name_lower in entity_lower or entity_lower in name_lower:
                score = len(name_lower) / max(len(entity_lower), 1)
                if score > best_score:
                    best_score = score
                    best_match = entity_id
        
        return best_match if best_score > 0.3 else None
    
    def _calculate_subgraph_relevance(
        self,
        subgraph: SubGraph,
        query_entity_ids: List[str],
    ) -> float:
        """计算子图与查询的相关性"""
        if not subgraph.entities:
            return 0.0
        
        # 基于查询实体在子图中的中心性
        query_in_subgraph = sum(
            1 for e in subgraph.entities if e.id in query_entity_ids
        )
        
        # 基于关系密度
        relation_density = len(subgraph.relations) / max(len(subgraph.entities), 1)
        
        # 综合分数
        relevance = (query_in_subgraph / max(len(query_entity_ids), 1)) * 0.6 + \
                    min(relation_density, 1.0) * 0.4
        
        return min(relevance, 1.0)
    
    def _keyword_match_communities(
        self,
        query: str,
        top_k: int,
        level: int,
    ) -> List[CommunitySummary]:
        """基于关键词匹配社区"""
        if not self.community_detector:
            return []
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_summaries = []
        for summary in self.community_detector.community_summaries.values():
            if summary.level != level:
                continue
            
            # 计算关键词匹配分数
            summary_text = f"{summary.title} {summary.summary}".lower()
            summary_words = set(summary_text.split())
            
            overlap = len(query_words & summary_words)
            score = overlap / max(len(query_words), 1)
            
            # 检查关键实体匹配
            for key_entity in summary.key_entities:
                if key_entity.lower() in query_lower:
                    score += 0.2
            
            if score > 0:
                summary.relevance_score = score
                scored_summaries.append(summary)
        
        # 排序
        scored_summaries.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored_summaries[:top_k]
    
    async def _extract_query_entities(self, query: str) -> List[str]:
        """从查询中提取实体"""
        extracted = []
        query_lower = query.lower()
        
        # 1. 直接匹配已知实体
        for entity_name in self.kg.name_to_id.keys():
            if entity_name.lower() in query_lower:
                extracted.append(entity_name)
        
        # 2. 如果没有匹配，尝试使用嵌入相似度
        if not extracted and self.embedding_fn:
            try:
                # 获取所有实体嵌入
                all_entities = list(self.kg.name_to_id.keys())[:100]  # 限制数量
                
                if all_entities:
                    # 计算查询嵌入
                    query_embedding = self.embedding_fn([query])
                    if query_embedding:
                        # 计算相似度
                        similar = await self._find_similar_by_embedding(
                            query_embedding[0], all_entities, top_k=3
                        )
                        extracted.extend(similar)
            except Exception as e:
                logger.error(f"Entity extraction failed: {e}")
        
        return extracted[:5]  # 限制返回数量
    
    async def _find_similar_entities(
        self,
        text: str,
        entity_type: EntityType,
        top_k: int = 3,
    ) -> List[Entity]:
        """查找与文本相似的实体"""
        entities = self.kg.get_entities_by_type(entity_type)
        
        if not entities:
            return []
        
        if not self.embedding_fn:
            # 降级：简单文本匹配
            text_lower = text.lower()
            scored = []
            for entity in entities:
                score = 0
                if entity.name.lower() in text_lower:
                    score = 1.0
                elif text_lower in entity.name.lower():
                    score = 0.8
                else:
                    # 关键词匹配
                    keywords = entity.properties.get("keywords", [])
                    matches = sum(1 for kw in keywords if kw in text_lower)
                    score = matches / max(len(keywords), 1) * 0.5
                
                if score > 0:
                    scored.append((entity, score))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            return [e for e, _ in scored[:top_k]]
        
        # 使用嵌入相似度
        try:
            text_embedding = self.embedding_fn([text])
            if not text_embedding:
                return []
            
            import numpy as np
            query_vec = np.array(text_embedding[0])
            
            scored = []
            for entity in entities:
                if entity.embedding:
                    entity_vec = np.array(entity.embedding)
                    similarity = np.dot(query_vec, entity_vec) / (
                        np.linalg.norm(query_vec) * np.linalg.norm(entity_vec) + 1e-8
                    )
                    scored.append((entity, float(similarity)))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            return [e for e, _ in scored[:top_k]]
        except Exception as e:
            logger.error(f"Embedding similarity search failed: {e}")
            return []
    
    async def _find_similar_by_embedding(
        self,
        query_embedding: List[float],
        entity_names: List[str],
        top_k: int = 3,
    ) -> List[str]:
        """基于嵌入查找相似实体名称"""
        try:
            # 获取或生成实体嵌入
            entity_embeddings = []
            valid_names = []
            
            for name in entity_names:
                if name in self._entity_embeddings:
                    entity_embeddings.append(self._entity_embeddings[name])
                    valid_names.append(name)
                else:
                    # 生成嵌入
                    embedding = self.embedding_fn([name])
                    if embedding:
                        self._entity_embeddings[name] = embedding[0]
                        entity_embeddings.append(embedding[0])
                        valid_names.append(name)
            
            if not entity_embeddings:
                return []
            
            import numpy as np
            query_vec = np.array(query_embedding)
            
            scored = []
            for name, emb in zip(valid_names, entity_embeddings):
                emb_vec = np.array(emb)
                similarity = np.dot(query_vec, emb_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(emb_vec) + 1e-8
                )
                scored.append((name, float(similarity)))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            return [name for name, _ in scored[:top_k] if scored[0][1] > 0.5]
        except Exception as e:
            logger.error(f"Embedding similarity failed: {e}")
            return []
    
    def _find_reasoning_paths(
        self,
        entity_names: List[str],
        max_paths: int = 3,
    ) -> List[List[str]]:
        """查找实体之间的推理路径"""
        if len(entity_names) < 2:
            return []
        
        paths = []
        
        # 获取实体ID
        entity_ids = []
        for name in entity_names:
            entity = self.kg.get_entity_by_name(name)
            if entity:
                entity_ids.append(entity.id)
        
        if len(entity_ids) < 2:
            return []
        
        # 查找路径
        raw_paths = self.kg.find_paths(entity_ids[0], entity_ids[1], max_length=4)
        
        for path in raw_paths[:max_paths]:
            # 转换为实体名称路径
            name_path = []
            for node_id in path:
                entity = self.kg.get_entity(node_id)
                if entity:
                    name_path.append(entity.name)
            
            if name_path:
                paths.append(name_path)
        
        return paths
    
    def _filter_subgraph_by_context(
        self,
        subgraph: SubGraph,
        sales_stage: Optional[str],
        customer_type: Optional[str],
    ) -> SubGraph:
        """根据上下文过滤子图"""
        if not sales_stage and not customer_type:
            return subgraph
        
        # 获取与阶段/客户类型相关的实体ID
        relevant_ids = set()
        
        if sales_stage:
            stage_entity = None
            for entity in subgraph.entities:
                if entity.type == EntityType.SALES_STAGE:
                    if entity.properties.get("stage_code") == sales_stage:
                        stage_entity = entity
                        break
            
            if stage_entity:
                # 获取与该阶段相关的实体
                neighbors = self.kg.get_neighbors(
                    stage_entity.id,
                    [RelationType.APPLIES_TO_STAGE],
                    "in"
                )
                for neighbor, _ in neighbors:
                    relevant_ids.add(neighbor.id)
        
        if customer_type:
            for entity in subgraph.entities:
                if entity.type == EntityType.CUSTOMER_TYPE:
                    if customer_type.lower() in entity.name.lower():
                        neighbors = self.kg.get_neighbors(
                            entity.id,
                            [RelationType.SUITS_CUSTOMER],
                            "in"
                        )
                        for neighbor, _ in neighbors:
                            relevant_ids.add(neighbor.id)
        
        # 如果没有找到相关实体，返回原子图
        if not relevant_ids:
            return subgraph
        
        # 过滤实体
        filtered_entities = [
            e for e in subgraph.entities
            if e.id in relevant_ids or e.type in [EntityType.OBJECTION, EntityType.RESPONSE]
        ]
        
        # 过滤关系
        filtered_entity_ids = {e.id for e in filtered_entities}
        filtered_relations = [
            r for r in subgraph.relations
            if r.source_id in filtered_entity_ids and r.target_id in filtered_entity_ids
        ]
        
        return SubGraph(
            entities=filtered_entities,
            relations=filtered_relations,
            center_entity_id=subgraph.center_entity_id,
            hop_count=subgraph.hop_count,
            relevance_score=subgraph.relevance_score,
        )

