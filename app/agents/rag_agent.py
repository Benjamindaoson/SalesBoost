"""
RAG Knowledge Agent
检索话术 / 案例 / 异议策略
强制输出结构：{content: str, source_citations: List[str]}
❌ 禁止幻觉，不知则由兜底逻辑处理

支持三种检索模式：
1. 基础向量检索 (KnowledgeService)
2. 高级 RAG (AdvancedRAGService) - 混合检索、Reranker、查询扩展
3. GraphRAG (GraphRAGService) - 知识图谱增强，支持多跳推理
"""
import logging
from typing import Dict, Any, List, Optional
from app.schemas.agent_outputs import RAGOutput, RAGItem
from app.schemas.fsm import SalesStage

logger = logging.getLogger(__name__)


class RAGAgent:
    """
    RAG 知识检索 Agent
    
    核心职责：
    - 检索相关话术、案例、异议处理策略
    - 强制输出来源引用（source_citations）
    - 禁止幻觉，不知则触发兜底
    
    检索内容类型：
    - script: 话术模板
    - case: 成功案例
    - strategy: 销售策略
    - faq: 常见问答
    
    检索模式：
    - basic: 基础向量检索
    - advanced: 高级 RAG（混合检索 + Reranker）
    - graph: GraphRAG（知识图谱增强）
    - hybrid: 混合模式（向量 + 图，推荐）
    """
    
    def __init__(
        self,
        use_advanced_rag: bool = True,
        use_graph_rag: bool = True,
    ):
        """
        初始化 RAG Agent
        
        Args:
            use_advanced_rag: 是否使用高级RAG（2026年最先进技术）
            use_graph_rag: 是否使用 GraphRAG（知识图谱增强）
        """
        self.use_advanced_rag = use_advanced_rag
        self.use_graph_rag = use_graph_rag
        self.graph_rag = None
        
        # 初始化高级 RAG
        if use_advanced_rag:
            try:
                from app.services.advanced_rag_service import AdvancedRAGService
                # 金融场景优化配置
                self.advanced_rag = AdvancedRAGService(
                    enable_hybrid=True,
                    enable_reranker=True,
                    enable_query_expansion=True,
                    enable_rag_fusion=False,  # 默认关闭，按需启用
                    enable_adaptive=True,  # 自适应检索
                    enable_multi_vector=False,  # 默认关闭
                    enable_context_compression=False,  # 默认关闭
                    enable_caching=True,  # 启用缓存
                    financial_optimized=True,  # 金融场景优化
                )
                logger.info("Advanced RAG service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize advanced RAG: {e}, falling back to basic")
                self.use_advanced_rag = False
        
        # 初始化 GraphRAG
        if use_graph_rag:
            try:
                from app.services.graph_rag_service import GraphRAGService
                self.graph_rag = GraphRAGService(
                    enable_communities=True,
                )
                logger.info("GraphRAG service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize GraphRAG: {e}")
                self.use_graph_rag = False
        
        # 降级到基础服务
        if not self.use_advanced_rag:
            from app.services.knowledge_service import KnowledgeService
            self.knowledge_service = KnowledgeService()
            logger.info("Basic RAG service initialized")
    
    async def retrieve(
        self,
        query: str,
        stage: SalesStage,
        context: Dict[str, Any],
        top_k: int = 3,
        mode: str = "hybrid",
    ) -> RAGOutput:
        """
        检索相关知识
        
        Args:
            query: 检索查询
            stage: 当前销售阶段
            context: 上下文信息
            top_k: 返回结果数量
            mode: 检索模式 ("basic" | "advanced" | "graph" | "hybrid")
            
        Returns:
            RAG 检索结果
        """
        logger.info(f"RAG retrieval: query='{query[:50]}...', stage={stage.value}, mode={mode}")
        
        # 构建检索查询，包含阶段信息以增强相关性
        search_query = f"{stage.value}: {query}"
        
        # 构建上下文（用于自适应检索和查询扩展）
        rag_context = {
            **context,
            "stage": stage.value,
        }
        
        # 判断是否使用RAG-Fusion（复杂查询或异议处理）
        use_rag_fusion = (
            "异议" in query or
            "反对" in query or
            "担心" in query or
            stage in ["OBJECTION_HANDLING", "CLOSING"]
        )
        
        # 判断是否需要 GraphRAG（多跳推理场景）
        use_graph = (
            mode in ["graph", "hybrid"] and
            self.use_graph_rag and
            self.graph_rag is not None
        )
        
        vector_results = []
        graph_results = None
        
        # 1. 向量检索（高级 RAG 或基础）
        if mode != "graph":
            if self.use_advanced_rag and hasattr(self, 'advanced_rag'):
                try:
                    vector_results = await self.advanced_rag.search(
                        query=search_query,
                        top_k=top_k,
                        filter_meta=context.get("filter_meta"),
                        use_rag_fusion=use_rag_fusion,
                        context=rag_context,
                        use_adaptive=True,
                        use_multi_vector=False,
                        use_compression=False,
                    )
                except Exception as e:
                    logger.error(f"Advanced RAG search failed: {e}, falling back to basic")
                    vector_results = []
            
            if not vector_results and hasattr(self, 'knowledge_service'):
                try:
                    vector_results = self.knowledge_service.query(
                        text=search_query,
                        top_k=top_k,
                        min_relevance=0.5,
                        rerank=True,
                    )
                except Exception as e:
                    logger.error(f"Vector search failed: {e}")
                    vector_results = []
        
        # 2. GraphRAG 检索
        if use_graph:
            try:
                graph_results = await self.graph_rag.search(
                    query=query,
                    stage=stage.value,
                    mode="hybrid" if mode == "hybrid" else "local",
                    top_k=top_k,
                    context=rag_context,
                )
            except Exception as e:
                logger.error(f"GraphRAG search failed: {e}")
                graph_results = None
        
        # 3. 融合结果
        if mode == "hybrid" and vector_results and graph_results:
            results = self._fuse_results(vector_results, graph_results, top_k)
        elif graph_results and graph_results.local_subgraphs:
            results = self._convert_graph_results(graph_results)
        else:
            results = vector_results
        
        if not results:
            return RAGOutput(
                retrieved_content=[],
                query_understanding=f"查询：{query}",
                no_result_fallback=True,
                fallback_reason=f"知识库中未找到相关内容",
            )
        
        retrieved_items = []
        for item in results:
            # 解析元数据
            meta = item.get("metadata", {})
            content_type = meta.get("type", "knowledge")
            source = meta.get("source", "Knowledge Base")
            
            # 添加 GraphRAG 来源标记
            if item.get("graph_source"):
                source = f"{source} (GraphRAG)"
            
            # 使用改进的相关性分数
            relevance_score = item.get("relevance_score", item.get("fused_score", 1.0 - item.get("distance", 0)))
            
            retrieved_items.append(RAGItem(
                content=item["content"],
                source_citations=[source],
                relevance_score=relevance_score,
                content_type=content_type,
            ))
        
        # 添加推理路径信息（如果有）
        reasoning_info = ""
        if graph_results and graph_results.reasoning_paths:
            paths_str = "; ".join([" -> ".join(p) for p in graph_results.reasoning_paths[:2]])
            reasoning_info = f" [推理路径: {paths_str}]"
        
        return RAGOutput(
            retrieved_content=retrieved_items,
            query_understanding=f"查询：{query}，阶段：{stage.value}{reasoning_info}",
            no_result_fallback=False,
            fallback_reason=None,
        )
    
    def _fuse_results(
        self,
        vector_results: List[Dict[str, Any]],
        graph_results: Any,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        融合向量检索和图检索结果（RRF 算法）
        
        Args:
            vector_results: 向量检索结果
            graph_results: GraphRAG 检索结果
            top_k: 返回数量
            
        Returns:
            融合后的结果
        """
        try:
            from app.services.graph_rag_service import fuse_results_rrf
            return fuse_results_rrf(
                vector_results=vector_results,
                graph_results=graph_results,
                vector_weight=0.6,
                graph_weight=0.4,
            )[:top_k]
        except Exception as e:
            logger.error(f"Result fusion failed: {e}")
            return vector_results
    
    def _convert_graph_results(self, graph_results: Any) -> List[Dict[str, Any]]:
        """
        将 GraphRAG 结果转换为标准格式
        
        Args:
            graph_results: GraphRAG 检索结果
            
        Returns:
            标准格式的结果列表
        """
        results = []
        
        # 从子图中提取
        for subgraph in graph_results.local_subgraphs:
            for entity in subgraph.entities:
                # 优先提取话术和应对策略
                if entity.type.value in ["Response", "Script"]:
                    results.append({
                        "content": entity.name,
                        "metadata": {
                            "type": entity.type.value.lower(),
                            "source": "Knowledge Graph",
                            **entity.properties,
                        },
                        "relevance_score": subgraph.relevance_score,
                        "graph_source": "entity",
                    })
        
        # 从社区摘要中提取
        for summary in graph_results.community_summaries:
            results.append({
                "content": summary.summary,
                "metadata": {
                    "type": "community_summary",
                    "source": "Knowledge Graph",
                    "title": summary.title,
                    "key_entities": summary.key_entities,
                },
                "relevance_score": summary.relevance_score,
                "graph_source": "community",
            })
        
        return results
    
    async def add_knowledge(
        self,
        content: str,
        sources: List[str],
        stage: SalesStage,
        content_type: str,
    ) -> bool:
        """
        添加知识条目（用于知识库扩展）
        
        Args:
            content: 知识内容
            sources: 来源引用
            stage: 适用阶段
            content_type: 内容类型
            
        Returns:
            是否添加成功
        """
        # 添加到向量知识库
        if hasattr(self, 'knowledge_service'):
            try:
                self.knowledge_service.add_document(
                    content=content,
                    meta={
                        "sources": sources,
                        "stage": stage.value,
                        "type": content_type,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to add to vector knowledge base: {e}")
        
        # 添加到 GraphRAG（如果启用）
        if self.use_graph_rag and self.graph_rag:
            try:
                import uuid
                doc_id = str(uuid.uuid4())[:8]
                await self.graph_rag.ingest_document(
                    doc_id=doc_id,
                    text=content,
                    metadata={
                        "sources": sources,
                        "stage": stage.value,
                        "type": content_type,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to add to GraphRAG: {e}")
        
        logger.info(f"Knowledge added: stage={stage.value}, type={content_type}")
        return True
    
    async def retrieve_for_objection(
        self,
        objection_text: str,
        stage: Optional[SalesStage] = None,
        customer_type: Optional[str] = None,
        top_k: int = 5,
    ) -> RAGOutput:
        """
        专门针对异议的检索（利用 GraphRAG 的多跳推理能力）
        
        Args:
            objection_text: 客户异议文本
            stage: 当前销售阶段
            customer_type: 客户类型
            top_k: 返回数量
            
        Returns:
            包含异议应对策略的 RAG 输出
        """
        if not self.use_graph_rag or not self.graph_rag:
            # 降级到普通检索
            return await self.retrieve(
                query=objection_text,
                stage=stage or SalesStage.OBJECTION_HANDLING,
                context={},
                top_k=top_k,
                mode="advanced",
            )
        
        try:
            # 使用 GraphRAG 的专用异议检索
            subgraph = await self.graph_rag.graph_retriever.retrieve_for_objection(
                objection_text=objection_text,
                sales_stage=stage.value if stage else None,
                customer_type=customer_type,
                top_k=top_k,
            )
            
            if not subgraph.entities:
                return RAGOutput(
                    retrieved_content=[],
                    query_understanding=f"异议：{objection_text}",
                    no_result_fallback=True,
                    fallback_reason="未找到相关异议处理策略",
                )
            
            # 转换为 RAGItem
            retrieved_items = []
            for entity in subgraph.entities:
                if entity.type.value in ["Response", "Script"]:
                    retrieved_items.append(RAGItem(
                        content=entity.name,
                        source_citations=["Knowledge Graph - 异议处理"],
                        relevance_score=subgraph.relevance_score,
                        content_type="objection_response",
                    ))
            
            return RAGOutput(
                retrieved_content=retrieved_items,
                query_understanding=f"异议：{objection_text}，找到 {len(retrieved_items)} 条应对策略",
                no_result_fallback=len(retrieved_items) == 0,
                fallback_reason=None if retrieved_items else "未找到直接匹配的应对策略",
            )
            
        except Exception as e:
            logger.error(f"Objection retrieval failed: {e}")
            return await self.retrieve(
                query=objection_text,
                stage=stage or SalesStage.OBJECTION_HANDLING,
                context={},
                top_k=top_k,
                mode="advanced",
            )
    
    def get_graph_statistics(self) -> Optional[Dict[str, Any]]:
        """获取 GraphRAG 统计信息"""
        if self.use_graph_rag and self.graph_rag:
            return self.graph_rag.get_statistics()
        return None
