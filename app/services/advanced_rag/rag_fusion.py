"""
RAG-Fusion - 多查询融合检索
2026年最先进的多查询RAG技术
"""
import logging
from typing import List, Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)


class RAGFusion:
    """
    RAG-Fusion实现
    
    核心思想：
    1. 生成多个查询变体
    2. 并行检索每个变体
    3. 融合结果并去重
    4. 重排序最终结果
    """
    
    def __init__(
        self,
        retriever,  # HybridRetriever实例
        query_expander,  # QueryExpander实例
        reranker=None,  # Reranker实例（可选）
    ):
        """
        初始化RAG-Fusion
        
        Args:
            retriever: 混合检索器
            query_expander: 查询扩展器
            reranker: Reranker（可选）
        """
        self.retriever = retriever
        self.query_expander = query_expander
        self.reranker = reranker
    
    async def fused_search(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        num_query_variants: int = 3,
        filter_meta: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        RAG-Fusion检索
        
        Args:
            query: 原始查询
            context: 上下文信息
            top_k: 最终返回数量
            num_query_variants: 查询变体数量
            filter_meta: 元数据过滤
            
        Returns:
            融合后的检索结果
        """
        # Step 1: 查询扩展
        query_variants = await self.query_expander.expand_query(
            original_query=query,
            context=context,
            num_variants=num_query_variants,
        )
        
        logger.info(f"RAG-Fusion: Generated {len(query_variants)} query variants")
        
        # Step 2: 并行检索每个查询变体
        retrieval_tasks = []
        for variant in query_variants:
            # 注意：这里需要根据实际retriever接口调整
            # 假设retriever有hybrid_search方法
            task = self._retrieve_variant(
                variant=variant,
                top_k=top_k * 2,  # 每个变体检索更多候选
                filter_meta=filter_meta,
            )
            retrieval_tasks.append(task)
        
        # 并行执行检索
        all_results = await asyncio.gather(*retrieval_tasks)
        
        # Step 3: 融合结果（使用RRF）
        fused_results = self._fuse_results(
            all_results=all_results,
            top_k=top_k * 2,  # 融合后保留更多候选用于rerank
        )
        
        # Step 4: 去重
        deduplicated = self._deduplicate(fused_results)
        
        # Step 5: Rerank（如果可用）
        if self.reranker and deduplicated:
            final_results = self._apply_reranker(
                query=query,
                results=deduplicated,
                top_k=top_k,
            )
        else:
            final_results = deduplicated[:top_k]
        
        logger.info(
            f"RAG-Fusion completed: {len(query_variants)} variants → "
            f"{len(fused_results)} fused → {len(final_results)} final"
        )
        
        return final_results
    
    async def _retrieve_variant(
        self,
        variant: str,
        top_k: int,
        filter_meta: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """检索单个查询变体"""
        try:
            # 这里需要根据实际retriever接口调整
            # 假设有hybrid_search方法
            if hasattr(self.retriever, 'hybrid_search'):
                results = self.retriever.hybrid_search(
                    query=variant,
                    top_k=top_k,
                    filter_meta=filter_meta,
                )
            else:
                # 降级：使用向量检索
                results = self.retriever.vector_search(
                    query=variant,
                    top_k=top_k,
                    filter_meta=filter_meta,
                )
            
            return results
        except Exception as e:
            logger.error(f"Retrieval failed for variant '{variant}': {e}")
            return []
    
    def _fuse_results(
        self,
        all_results: List[List[Dict[str, Any]]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        融合多个检索结果（使用RRF）
        
        Args:
            all_results: 每个查询变体的检索结果列表
            top_k: 返回数量
        """
        # 构建文档到RRF分数的映射
        doc_scores = {}  # {content: rrf_score}
        doc_metadata = {}  # {content: metadata}
        rrf_k = 60
        
        # 对每个查询变体的结果计算RRF分数
        for query_rank, results in enumerate(all_results, 1):
            for result in results:
                content = result.get("content", "")
                if not content:
                    continue
                
                # 获取原始rank（如果存在）
                rank = result.get("rank", query_rank * 100)  # 降级：使用查询顺序
                
                # RRF分数
                rrf_score = 1.0 / (rrf_k + rank)
                
                if content not in doc_scores:
                    doc_scores[content] = 0
                    doc_metadata[content] = result.get("metadata", {})
                
                # 累加RRF分数（多个查询变体都检索到同一文档时分数更高）
                doc_scores[content] += rrf_score
        
        # 按RRF分数排序
        sorted_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        # 格式化结果
        fused_results = []
        for rank, (content, rrf_score) in enumerate(sorted_docs, 1):
            fused_results.append({
                "content": content,
                "metadata": doc_metadata.get(content, {}),
                "rrf_score": rrf_score,
                "rank": rank,
                "source": "rag_fusion",
            })
        
        return fused_results
    
    def _deduplicate(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """去重（基于内容相似度）"""
        seen = set()
        deduplicated = []
        
        for result in results:
            content = result.get("content", "")
            # 简单去重：完全相同的文档
            if content and content not in seen:
                seen.add(content)
                deduplicated.append(result)
        
        return deduplicated
    
    def _apply_reranker(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """应用Reranker重排序"""
        if not self.reranker or not results:
            return results[:top_k]
        
        # 提取文档内容
        documents = [r["content"] for r in results]
        
        # Rerank
        reranked = self.reranker.rerank(
            query=query,
            documents=documents,
            top_k=top_k,
        )
        
        # 合并元数据
        content_to_metadata = {r["content"]: r.get("metadata", {}) for r in results}
        
        final_results = []
        for rerank_result in reranked:
            content = rerank_result["content"]
            final_results.append({
                "content": content,
                "metadata": content_to_metadata.get(content, {}),
                "rerank_score": rerank_result["score"],
                "rank": rerank_result["rank"],
                "source": "rag_fusion_reranked",
            })
        
        return final_results


