"""
自适应检索器 - Adaptive Retrieval Strategy
根据查询类型和金融场景特征，自动选择最佳检索策略
"""
import logging
import re
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """查询类型"""
    FACTUAL = "factual"          # 事实性查询（费率、条款等）
    EXPLORATORY = "exploratory"  # 探索性查询（产品推荐、比较）
    COMPARATIVE = "comparative"  # 比较性查询（A vs B）
    OBJECTION = "objection"      # 异议处理（价格异议、信任异议）
    PROCEDURAL = "procedural"    # 流程性查询（如何办理、步骤）


class AdaptiveRetriever:
    """
    自适应检索器
    
    针对金融场景优化：
    - 事实性查询 → 精确检索 + 元数据过滤
    - 探索性查询 → 宽泛检索 + 多样性
    - 比较性查询 → 多文档检索
    - 异议处理 → RAG-Fusion + 上下文压缩
    """
    
    def __init__(self, base_retriever):
        """
        初始化自适应检索器
        
        Args:
            base_retriever: 基础检索器（AdvancedRAGService实例）
        """
        self.base_retriever = base_retriever
        
        # 金融场景关键词
        self.financial_keywords = {
            QueryType.FACTUAL: ["费率", "年费", "额度", "利率", "期限", "条款", "规定"],
            QueryType.EXPLORATORY: ["推荐", "适合", "选择", "哪个", "什么", "如何"],
            QueryType.COMPARATIVE: ["对比", "比较", "区别", "差异", "哪个好", "vs"],
            QueryType.OBJECTION: ["贵", "价格", "费用", "不信", "担心", "风险"],
            QueryType.PROCEDURAL: ["如何", "怎么", "步骤", "流程", "办理", "申请"],
        }
    
    def classify_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> QueryType:
        """
        分类查询类型
        
        Args:
            query: 查询文本
            context: 上下文（如销售阶段）
            
        Returns:
            查询类型
        """
        query_lower = query.lower()
        
        # 检查上下文中的销售阶段
        if context:
            stage = context.get("stage", "")
            if "objection" in stage.lower() or "异议" in stage:
                return QueryType.OBJECTION
        
        # 基于关键词分类
        scores = {}
        for query_type, keywords in self.financial_keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            scores[query_type] = score
        
        # 找到得分最高的类型
        max_score = max(scores.values())
        if max_score > 0:
            for qtype, score in scores.items():
                if score == max_score:
                    return qtype
        
        # 默认：探索性查询
        return QueryType.EXPLORATORY
    
    async def adaptive_search(
        self,
        query: str,
        top_k: int = 5,
        context: Optional[Dict[str, Any]] = None,
        filter_meta: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        自适应检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            context: 上下文信息
            filter_meta: 元数据过滤
            
        Returns:
            检索结果
        """
        # 1. 分类查询类型
        query_type = self.classify_query(query, context)
        
        logger.info(f"Query classified as: {query_type.value}")
        
        # 2. 根据查询类型选择策略
        if query_type == QueryType.FACTUAL:
            return await self._factual_search(query, top_k, filter_meta)
        elif query_type == QueryType.EXPLORATORY:
            return await self._exploratory_search(query, top_k, filter_meta)
        elif query_type == QueryType.COMPARATIVE:
            return await self._comparative_search(query, top_k, filter_meta)
        elif query_type == QueryType.OBJECTION:
            return await self._objection_search(query, top_k, context, filter_meta)
        elif query_type == QueryType.PROCEDURAL:
            return await self._procedural_search(query, top_k, filter_meta)
        else:
            # 默认策略
            return await self.base_retriever.search(query, top_k, filter_meta)
    
    async def _factual_search(
        self,
        query: str,
        top_k: int,
        filter_meta: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """事实性查询：精确检索 + 元数据过滤"""
        # 增强元数据过滤（针对金融数据）
        enhanced_filter = filter_meta or {}
        
        # 提取金融实体，用于精确过滤
        from app.services.advanced_rag.context_compressor import ContextCompressor
        compressor = ContextCompressor()
        entities = compressor.extract_financial_entities(query)
        
        # 如果查询包含产品名称，添加到过滤条件
        if entities["products"]:
            enhanced_filter["product_name"] = {"$in": entities["products"]}
        
        # 使用混合检索 + Reranker（高精度）
        return await self.base_retriever.search(
            query=query,
            top_k=top_k,
            filter_meta=enhanced_filter,
            use_rag_fusion=False,  # 事实性查询不需要Fusion
        )
    
    async def _exploratory_search(
        self,
        query: str,
        top_k: int,
        filter_meta: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """探索性查询：宽泛检索 + 多样性"""
        # 检索更多候选以增加多样性
        results = await self.base_retriever.search(
            query=query,
            top_k=top_k * 2,  # 检索更多
            filter_meta=filter_meta,
            use_rag_fusion=False,
        )
        
        # 多样性去重（基于内容相似度）
        diverse_results = self._diversify_results(results, top_k)
        
        return diverse_results
    
    async def _comparative_search(
        self,
        query: str,
        top_k: int,
        filter_meta: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """比较性查询：多文档检索"""
        # 提取比较对象
        comparison_items = self._extract_comparison_items(query)
        
        # 为每个比较对象检索
        all_results = []
        for item in comparison_items:
            item_results = await self.base_retriever.search(
                query=f"{item} {query}",
                top_k=top_k,
                filter_meta=filter_meta,
            )
            all_results.extend(item_results)
        
        # 去重和排序
        unique_results = self._deduplicate_results(all_results)
        return unique_results[:top_k]
    
    async def _objection_search(
        self,
        query: str,
        top_k: int,
        context: Optional[Dict],
        filter_meta: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """异议处理：RAG-Fusion + 上下文压缩"""
        # 使用RAG-Fusion（最高准确率）
        results = await self.base_retriever.search(
            query=query,
            top_k=top_k * 2,  # 检索更多用于压缩
            filter_meta=filter_meta,
            use_rag_fusion=True,  # 启用Fusion
            context=context,
        )
        
        # 上下文压缩（减少token消耗）
        if results and len(results) > top_k:
            from app.services.advanced_rag.context_compressor import ContextCompressor
            compressor = ContextCompressor()
            
            documents = [r["content"] for r in results]
            compressed = await compressor.compress(
                query=query,
                documents=documents,
                max_tokens=300,  # 压缩到300 tokens
                preserve_financial_data=True,
            )
            
            # 更新结果
            for i, comp in enumerate(compressed):
                if i < len(results):
                    results[i]["content"] = comp["compressed"]
                    results[i]["compression_ratio"] = comp["compression_ratio"]
        
        return results[:top_k]
    
    async def _procedural_search(
        self,
        query: str,
        top_k: int,
        filter_meta: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """流程性查询：按步骤检索"""
        # 增强查询（添加"步骤"、"流程"关键词）
        enhanced_query = f"如何 {query} 步骤 流程"
        
        return await self.base_retriever.search(
            query=enhanced_query,
            top_k=top_k,
            filter_meta=filter_meta,
            use_rag_fusion=False,
        )
    
    def _extract_comparison_items(self, query: str) -> List[str]:
        """提取比较对象"""
        # 简单实现：查找"vs"、"对比"等关键词
        items = []
        
        # 查找"vs"、"对比"等
        vs_pattern = r'(\S+)\s*(?:vs|对比|比较|和)\s*(\S+)'
        match = re.search(vs_pattern, query, re.IGNORECASE)
        if match:
            items.extend([match.group(1), match.group(2)])
        
        return items if items else [query]
    
    def _diversify_results(
        self,
        results: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """增加结果多样性"""
        if len(results) <= top_k:
            return results
        
        # 简单多样性策略：选择不同来源/类型的结果
        diverse = []
        seen_sources = set()
        seen_types = set()
        
        for result in results:
            if len(diverse) >= top_k:
                break
            
            source = result.get("metadata", {}).get("source", "")
            content_type = result.get("metadata", {}).get("type", "")
            
            # 优先选择新来源/类型
            if source not in seen_sources or content_type not in seen_types:
                diverse.append(result)
                seen_sources.add(source)
                seen_types.add(content_type)
        
        # 如果还不够，添加剩余结果
        for result in results:
            if len(diverse) >= top_k:
                break
            if result not in diverse:
                diverse.append(result)
        
        return diverse[:top_k]
    
    def _deduplicate_results(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """去重结果"""
        seen = set()
        unique = []
        
        for result in results:
            content = result.get("content", "")
            # 简单去重：完全相同的文档
            if content and content not in seen:
                seen.add(content)
                unique.append(result)
        
        # 按相关性排序
        unique.sort(key=lambda x: x.get("rerank_score", x.get("relevance_score", 0)), reverse=True)
        
        return unique


