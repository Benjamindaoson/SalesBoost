"""
GraphRAG 统一服务 - 知识图谱增强的 RAG 系统

整合图构建、社区检测、图检索和向量检索，提供统一的检索接口。
"""
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from app.core.config import get_settings
from app.services.graph_rag.graph_schema import (
    Entity,
    EntityType,
    Triple,
    SubGraph,
    CommunitySummary,
    GraphRAGResult,
)
from app.services.graph_rag.graph_builder import SalesKnowledgeGraph
from app.services.graph_rag.relation_extractor import RelationExtractor
from app.services.graph_rag.community_detector import CommunityDetector
from app.services.graph_rag.graph_retriever import GraphRetriever
from app.services.graph_rag.explainability import ExplainabilityModule, ExplainableResult

logger = logging.getLogger(__name__)


class GraphRAGService:
    """
    GraphRAG 统一服务
    
    功能：
    - 知识图谱构建和管理
    - 文档摄入和关系提取
    - 混合检索（向量 + 图）
    - 结果融合（RRF 算法）
    """
    
    def __init__(
        self,
        org_id: Optional[str] = None,
        storage_path: Optional[str] = None,
        enable_communities: bool = True,
        llm_client=None,
        embedding_fn=None,
    ):
        """
        初始化 GraphRAG 服务
        
        Args:
            org_id: 组织ID（支持多租户）
            storage_path: 图存储路径
            enable_communities: 是否启用社区检测
            llm_client: LLM 客户端
            embedding_fn: 嵌入函数
        """
        self.org_id = org_id or "public"
        self.storage_path = storage_path or "./graph_db"
        self.enable_communities = enable_communities
        
        # 初始化 LLM 客户端
        if llm_client:
            self.llm_client = llm_client
        else:
            self.llm_client = self._init_llm_client()
        
        # 初始化嵌入函数
        if embedding_fn:
            self.embedding_fn = embedding_fn
        else:
            self.embedding_fn = self._init_embedding_fn()
        
        # 初始化知识图谱
        self.knowledge_graph = SalesKnowledgeGraph(
            storage_path=self.storage_path,
            org_id=self.org_id,
        )
        
        # 初始化关系提取器
        self.relation_extractor = RelationExtractor(
            llm_client=self.llm_client,
            use_rules=True,
        )
        
        # 初始化社区检测器
        self.community_detector = None
        if enable_communities:
            self.community_detector = CommunityDetector(
                knowledge_graph=self.knowledge_graph,
                llm_client=self.llm_client,
            )
        
        # 初始化图检索器
        self.graph_retriever = GraphRetriever(
            knowledge_graph=self.knowledge_graph,
            community_detector=self.community_detector,
            embedding_fn=self.embedding_fn,
        )
        
        # 初始化可解释性模块
        self.explainability = ExplainabilityModule(
            knowledge_graph=self.knowledge_graph,
        )
        
        logger.info(f"GraphRAG service initialized for org: {self.org_id}")
    
    def _init_llm_client(self):
        """初始化 LLM 客户端"""
        try:
            settings = get_settings()
            if settings.OPENAI_API_KEY:
                from openai import OpenAI
                return OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                )
        except Exception as e:
            logger.warning(f"Failed to initialize LLM client: {e}")
        return None
    
    def _init_embedding_fn(self):
        """初始化嵌入函数"""
        try:
            settings = get_settings()
            if settings.OPENAI_API_KEY:
                from openai import OpenAI
                client = OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                )
                model = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
                
                def embedding_fn(texts: List[str]) -> List[List[float]]:
                    resp = client.embeddings.create(model=model, input=texts)
                    return [item.embedding for item in resp.data]
                
                return embedding_fn
        except Exception as e:
            logger.warning(f"Failed to initialize embedding function: {e}")
        return None
    
    async def search(
        self,
        query: str,
        stage: Optional[str] = None,
        mode: str = "hybrid",
        top_k: int = 5,
        context: Optional[Dict[str, Any]] = None,
        include_explanation: bool = False,
    ) -> GraphRAGResult:
        """
        GraphRAG 检索入口
        
        Args:
            query: 查询文本
            stage: 销售阶段（可选）
            mode: 检索模式 ("local" | "global" | "hybrid")
            top_k: 返回数量
            context: 上下文信息
            include_explanation: 是否包含详细解释
            
        Returns:
            GraphRAG 检索结果
        """
        start_time = time.time()
        
        # 提取查询实体
        query_entities = await self.graph_retriever._extract_query_entities(query)
        
        if mode == "local":
            # 仅局部检索
            result = await self._local_search(query, query_entities, stage, top_k)
        elif mode == "global":
            # 仅全局检索
            result = await self._global_search(query, top_k)
        else:
            # 混合检索（推荐）
            result = await self._hybrid_search(query, query_entities, stage, top_k, context)
        
        result.retrieval_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"GraphRAG search completed: mode={mode}, "
            f"entities={result.total_entities}, time={result.retrieval_time_ms:.1f}ms"
        )
        
        return result
    
    async def search_with_explanation(
        self,
        query: str,
        stage: Optional[str] = None,
        mode: str = "hybrid",
        top_k: int = 5,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[GraphRAGResult, List[ExplainableResult]]:
        """
        带解释的 GraphRAG 检索
        
        Args:
            query: 查询文本
            stage: 销售阶段
            mode: 检索模式
            top_k: 返回数量
            context: 上下文信息
            
        Returns:
            (检索结果, 可解释结果列表)
        """
        # 执行检索
        result = await self.search(query, stage, mode, top_k, context)
        
        # 生成解释
        explainable_results = self.explainability.explain_result(result, query)
        
        return result, explainable_results
    
    def get_explanation_text(self, result: GraphRAGResult, query: str) -> str:
        """
        获取检索结果的文本解释
        
        Args:
            result: GraphRAG 检索结果
            query: 原始查询
            
        Returns:
            人类可读的解释文本
        """
        return self.explainability.generate_explanation_text(result, query)
    
    async def _local_search(
        self,
        query: str,
        query_entities: List[str],
        stage: Optional[str],
        top_k: int,
    ) -> GraphRAGResult:
        """局部检索：基于实体的子图检索"""
        result = GraphRAGResult(query=query, mode="local")
        
        if not query_entities:
            return result
        
        # 获取子图
        subgraph = await self.graph_retriever.retrieve_subgraph(
            query_entities=query_entities,
            max_hops=2,
            max_nodes=top_k * 4,
        )
        
        if subgraph.entities:
            result.local_subgraphs.append(subgraph)
            result.total_entities = len(subgraph.entities)
            result.total_relations = len(subgraph.relations)
        
        # 查找推理路径
        if len(query_entities) >= 2:
            result.reasoning_paths = self.graph_retriever._find_reasoning_paths(
                query_entities[:2]
            )
        
        result.build_context()
        return result
    
    async def _global_search(
        self,
        query: str,
        top_k: int,
    ) -> GraphRAGResult:
        """全局检索：基于社区摘要的检索"""
        result = GraphRAGResult(query=query, mode="global")
        
        if not self.community_detector:
            return result
        
        # 确保社区已检测
        if not self.community_detector.communities:
            self.community_detector.detect_communities(levels=2)
            await self.community_detector.generate_summaries(level=0)
        
        # 检索社区
        summaries = await self.graph_retriever.retrieve_by_community(
            query=query,
            top_k=top_k,
            level=0,
        )
        
        result.community_summaries = summaries
        result.build_context()
        return result
    
    async def _hybrid_search(
        self,
        query: str,
        query_entities: List[str],
        stage: Optional[str],
        top_k: int,
        context: Optional[Dict[str, Any]],
    ) -> GraphRAGResult:
        """混合检索：结合局部和全局"""
        result = await self.graph_retriever.hybrid_search(
            query=query,
            query_entities=query_entities,
            max_hops=2,
            max_local_nodes=top_k * 3,
            top_k_communities=min(top_k, 3),
        )
        
        return result
    
    async def ingest_document(
        self,
        doc_id: str,
        text: str,
        entities: Optional[List[Entity]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        摄入文档到知识图谱
        
        Args:
            doc_id: 文档ID
            text: 文档文本
            entities: 预提取的实体（可选）
            metadata: 文档元数据
            
        Returns:
            摄入统计
        """
        start_time = time.time()
        
        # 1. 如果没有提供实体，进行实体提取
        if not entities:
            entities = await self._extract_entities_from_text(text, doc_id)
        
        # 2. 提取关系
        new_entities, triples = await self.relation_extractor.extract_relations(
            text=text,
            entities=entities,
            doc_id=doc_id,
        )
        
        # 合并实体
        all_entities = entities + new_entities
        
        # 3. 添加到图中
        stats = self.knowledge_graph.add_document_to_graph(
            doc_id=doc_id,
            entities=all_entities,
            triples=triples,
        )
        
        # 4. 更新实体嵌入
        if self.embedding_fn:
            await self._update_entity_embeddings(all_entities)
        
        # 5. 保存图
        self.knowledge_graph.save()
        
        elapsed = (time.time() - start_time) * 1000
        
        result = {
            **stats,
            "doc_id": doc_id,
            "total_entities": len(all_entities),
            "total_triples": len(triples),
            "processing_time_ms": elapsed,
        }
        
        logger.info(f"Document ingested: {result}")
        return result
    
    async def _extract_entities_from_text(
        self,
        text: str,
        doc_id: str,
    ) -> List[Entity]:
        """从文本中提取实体"""
        entities = []
        
        # 使用关系提取器的规则提取
        objections = self.relation_extractor.extract_objections_from_text(text)
        entities.extend(objections)
        
        # 如果有 LLM，使用 LLM 提取更多实体
        if self.llm_client:
            try:
                from app.services.document_parser import EntityExtractor
                extractor = EntityExtractor(self.llm_client)
                result = await extractor.extract_entities_and_tags(text)
                
                # 转换为 Entity 对象
                for entity_name in result.get("entities", []):
                    entity = Entity(
                        id=f"entity_{hash(entity_name) % 10000}",
                        name=entity_name,
                        type=EntityType.KEYWORD,
                        source_doc_ids=[doc_id],
                    )
                    entities.append(entity)
            except Exception as e:
                logger.warning(f"LLM entity extraction failed: {e}")
        
        return entities
    
    async def _update_entity_embeddings(self, entities: List[Entity]) -> int:
        """更新实体嵌入"""
        if not self.embedding_fn:
            return 0
        
        updated = 0
        batch_size = 50
        
        # 过滤没有嵌入的实体
        entities_to_embed = [e for e in entities if e.embedding is None]
        
        for i in range(0, len(entities_to_embed), batch_size):
            batch = entities_to_embed[i:i + batch_size]
            texts = [e.name for e in batch]
            
            try:
                embeddings = self.embedding_fn(texts)
                
                for entity, embedding in zip(batch, embeddings):
                    entity.embedding = embedding
                    self.knowledge_graph.update_entity_embedding(entity.id, embedding)
                    updated += 1
            except Exception as e:
                logger.error(f"Failed to generate embeddings: {e}")
        
        return updated
    
    async def rebuild_communities(self, levels: int = 2) -> Dict[str, Any]:
        """
        重建社区结构
        
        Args:
            levels: 层次数量
            
        Returns:
            社区统计
        """
        if not self.community_detector:
            return {"error": "Community detection not enabled"}
        
        start_time = time.time()
        
        # 检测社区
        communities = self.community_detector.detect_communities(levels=levels)
        
        # 生成摘要
        summaries = []
        for level in range(levels):
            level_summaries = await self.community_detector.generate_summaries(
                level=level,
                force_regenerate=True,
            )
            summaries.extend(level_summaries)
        
        # 更新摘要嵌入
        if self.embedding_fn:
            await self.community_detector.update_summary_embeddings(self.embedding_fn)
        
        elapsed = (time.time() - start_time) * 1000
        
        return {
            "levels": levels,
            "total_communities": sum(len(c) for c in communities.values()),
            "total_summaries": len(summaries),
            "processing_time_ms": elapsed,
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        graph_stats = self.knowledge_graph.get_statistics()
        
        community_stats = {}
        if self.community_detector:
            community_stats = {
                "levels": len(self.community_detector.communities),
                "total_communities": sum(
                    len(c) for c in self.community_detector.communities.values()
                ),
                "total_summaries": len(self.community_detector.community_summaries),
            }
        
        return {
            "org_id": self.org_id,
            "graph": graph_stats,
            "communities": community_stats,
            "has_llm": self.llm_client is not None,
            "has_embedding": self.embedding_fn is not None,
        }
    
    def save(self) -> bool:
        """保存所有数据"""
        return self.knowledge_graph.save()
    
    def clear(self):
        """清空所有数据"""
        self.knowledge_graph.clear()
        if self.community_detector:
            self.community_detector.communities.clear()
            self.community_detector.community_summaries.clear()


def fuse_results_rrf(
    vector_results: List[Dict[str, Any]],
    graph_results: GraphRAGResult,
    vector_weight: float = 0.5,
    graph_weight: float = 0.5,
    k: int = 60,
) -> List[Dict[str, Any]]:
    """
    使用 Reciprocal Rank Fusion (RRF) 融合向量检索和图检索结果
    
    Args:
        vector_results: 向量检索结果
        graph_results: 图检索结果
        vector_weight: 向量结果权重
        graph_weight: 图结果权重
        k: RRF 参数
        
    Returns:
        融合后的结果列表
    """
    # 提取图结果中的内容
    graph_contents = []
    
    # 从子图中提取
    for subgraph in graph_results.local_subgraphs:
        for entity in subgraph.entities:
            if entity.type in [EntityType.RESPONSE, EntityType.SCRIPT]:
                graph_contents.append({
                    "content": entity.name,
                    "metadata": entity.properties,
                    "source": "graph_entity",
                    "entity_type": entity.type.value,
                })
    
    # 从社区摘要中提取
    for summary in graph_results.community_summaries:
        graph_contents.append({
            "content": summary.summary,
            "metadata": {"title": summary.title, "key_entities": summary.key_entities},
            "source": "community_summary",
            "relevance_score": summary.relevance_score,
        })
    
    # 计算 RRF 分数
    content_scores: Dict[str, float] = {}
    content_data: Dict[str, Dict] = {}
    
    # 向量结果 RRF
    for rank, result in enumerate(vector_results):
        content = result.get("content", "")
        if content:
            rrf_score = vector_weight / (k + rank + 1)
            content_scores[content] = content_scores.get(content, 0) + rrf_score
            content_data[content] = result
    
    # 图结果 RRF
    for rank, result in enumerate(graph_contents):
        content = result.get("content", "")
        if content:
            rrf_score = graph_weight / (k + rank + 1)
            content_scores[content] = content_scores.get(content, 0) + rrf_score
            if content not in content_data:
                content_data[content] = result
            else:
                # 合并元数据
                content_data[content]["graph_source"] = result.get("source")
    
    # 排序
    sorted_contents = sorted(
        content_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )
    
    # 构建结果
    fused_results = []
    for content, score in sorted_contents:
        result = content_data.get(content, {"content": content})
        result["fused_score"] = score
        fused_results.append(result)
    
    return fused_results

