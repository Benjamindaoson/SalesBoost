"""
Retriever V3 - 证据构造器
封装现有 RAG/GraphRAG，输出 EvidencePack
Fast Path: 只能用 light retrieval
GraphRAG: 只能 Slow Path 且 hard budget
"""
import logging
import time
from typing import Dict, Any, Optional
from app.schemas.v3_agent_outputs import EvidencePack, EvidenceItem
from app.schemas.fsm import SalesStage
from app.agents.rag_agent import RAGAgent
from app.services.model_gateway import ModelGateway, AgentType, LatencyMode, RoutingContext
from app.services.model_gateway.budget import BudgetManager

logger = logging.getLogger(__name__)


class RetrieverV3:
    """Retriever V3 - 证据构造器"""
    
    def __init__(
        self,
        model_gateway: ModelGateway,
        budget_manager: BudgetManager,
        hard_budget_limit: float = 2000,
        use_graphrag: bool = False,
    ):
        self.model_gateway = model_gateway
        self.budget_manager = budget_manager
        self.hard_budget_limit = hard_budget_limit
        self.use_graphrag = use_graphrag
        # 封装现有 RAG Agent
        self.rag_agent = RAGAgent(use_advanced_rag=True, use_graph_rag=True)
    
    async def retrieve(
        self,
        query: str,
        stage: SalesStage,
        context: Dict[str, Any],
        session_id: str,
        turn_number: int,
        latency_mode: LatencyMode,
        budget_remaining: float,
    ) -> EvidencePack:
        """
        检索证据
        
        Args:
            query: 查询文本
            stage: 销售阶段
            context: 上下文
            session_id: 会话ID
            turn_number: 轮次号
            latency_mode: 延迟模式（fast/slow）
            budget_remaining: 剩余预算
            
        Returns:
            EvidencePack
        """
        start_time = time.time()
        
        # 获取剩余预算
        if budget_remaining is None:
            budget_remaining = self.budget_manager.get_remaining_budget(session_id)
        
        # HR-2: 快路径不可阻塞，禁 GraphRAG
        # HR-1: 预算熔断，禁 GraphRAG
        hard_budget = self.hard_budget_limit or 0.01
        can_use_graphrag = (
            latency_mode == LatencyMode.SLOW and
            self.use_graphrag and
            budget_remaining >= hard_budget
        )
        
        context = {"session_id": session_id, "turn_number": turn_number}
        
        if latency_mode == LatencyMode.FAST:
            # Fast Path: 只允许 lightweight retrieval
            retrieval_mode = "lightweight"
            rag_output = await self.rag_agent.retrieve(
                query=query,
                stage=stage,
                context=context,
                top_k=3,
                mode="basic",  # 基础向量检索
            )
        elif can_use_graphrag:
            # Slow Path + 预算充足: 可以使用 GraphRAG
            retrieval_mode = "graphrag"
            rag_output = await self.rag_agent.retrieve(
                query=query,
                stage=stage,
                context=context,
                top_k=5,
                mode="hybrid",  # 混合模式（向量 + 图）
            )
        else:
            # Slow Path 但预算不足: 降级到向量检索
            retrieval_mode = "lightweight"
            rag_output = await self.rag_agent.retrieve(
                query=query,
                stage=stage,
                context=context,
                top_k=3,
                mode="basic",
            )
        
        # 转换为 EvidencePack
        evidence_items = []
        for item in rag_output.retrieved_content[:5]:
            # 确定 source_type
            source_type = "fact"
            if item.content_type == "script":
                source_type = "objection_playbook"
            elif item.content_type == "case":
                source_type = "graph_insight"
            elif item.content_type == "strategy":
                source_type = "policy"
            
            evidence_items.append(EvidenceItem(
                content=item.content,
                source=", ".join(item.source_citations) if item.source_citations else "unknown",
                source_type=source_type,
                confidence=item.relevance_score,
                relevance_score=item.relevance_score,
            ))
        
        retrieval_time_ms = (time.time() - start_time) * 1000
        
        # 计算整体置信度
        overall_confidence = (
            sum(item.confidence for item in evidence_items) / len(evidence_items)
            if evidence_items else 0.0
        )
        
        return EvidencePack(
            items=evidence_items,
            retrieval_mode=retrieval_mode,
            total_items=len(evidence_items),
            confidence=overall_confidence,
            retrieval_time_ms=retrieval_time_ms,
            graph_nodes_visited=None if retrieval_mode != "graphrag" else len(evidence_items),
        )
