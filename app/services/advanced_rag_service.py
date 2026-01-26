"""
高级RAG服务 - 集成所有2026年最先进技术
统一接口，向后兼容
针对金融场景优化
"""
import logging
import pickle
import hashlib
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.services.knowledge_service import KnowledgeService
from app.services.advanced_rag.hybrid_retriever import HybridRetriever
from app.services.advanced_rag.reranker import Reranker
from app.services.advanced_rag.query_expander import QueryExpander
from app.services.advanced_rag.rag_fusion import RAGFusion
from app.services.advanced_rag.context_compressor import ContextCompressor
from app.services.advanced_rag.adaptive_retriever import AdaptiveRetriever
from app.services.advanced_rag.multi_vector_retriever import MultiVectorRetriever
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AdvancedRAGService:
    """
    高级RAG服务
    
    集成2026年最先进的RAG技术：
    - 混合检索（向量 + BM25）
    - 专业Reranker
    - 查询扩展
    - RAG-Fusion多查询融合
    """
    
    def __init__(
        self,
        org_id: Optional[str] = None,
        enable_hybrid: bool = True,
        enable_reranker: bool = True,
        enable_query_expansion: bool = True,
        enable_rag_fusion: bool = False,  # 默认关闭（性能考虑）
        enable_adaptive: bool = True,  # 自适应检索
        enable_multi_vector: bool = False,  # 多向量检索（默认关闭）
        enable_context_compression: bool = False,  # 上下文压缩（默认关闭）
        enable_caching: bool = True,  # 查询缓存
        financial_optimized: bool = True,  # 金融场景优化
    ):
        """
        初始化高级RAG服务
        
        Args:
            org_id: 组织ID
            enable_hybrid: 启用混合检索
            enable_reranker: 启用Reranker
            enable_query_expansion: 启用查询扩展
            enable_rag_fusion: 启用RAG-Fusion（性能开销较大）
        """
        settings = get_settings()
        
        # 基础知识服务
        self.knowledge_service = KnowledgeService(org_id=org_id)
        
        # 混合检索器
        self.hybrid_retriever = None
        if enable_hybrid:
            try:
                # 初始化混合检索器（BM25索引稍后构建）
                self.hybrid_retriever = HybridRetriever(
                    vector_collection=self.knowledge_service.collection,
                    bm25_index=None,  # 稍后构建
                )
                
                # 尝试加载BM25索引缓存
                cached_index = self._load_bm25_index()
                if cached_index:
                    self.hybrid_retriever.bm25_index = cached_index
                    self.hybrid_retriever.has_bm25 = True
                
                logger.info("Hybrid retriever initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize hybrid retriever: {e}")
        
        # Reranker
        self.reranker = None
        if enable_reranker:
            try:
                # 优先使用BGE-Reranker（开源）
                self.reranker = Reranker(model_type="bge")
                if not self.reranker.reranker:
                    # 降级到Cohere（如果配置了API key）
                    if settings.OPENAI_API_KEY:  # 假设可以用OpenAI key或单独配置
                        # 这里可以添加Cohere配置
                        pass
                logger.info("Reranker initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize reranker: {e}")
        
        # 查询扩展器
        self.query_expander = None
        if enable_query_expansion:
            try:
                from openai import OpenAI
                llm_client = OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL
                ) if settings.OPENAI_API_KEY else None
                self.query_expander = QueryExpander(llm_client=llm_client)
                logger.info("Query expander initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize query expander: {e}")
        
        # RAG-Fusion
        self.rag_fusion = None
        if enable_rag_fusion and self.hybrid_retriever and self.query_expander:
            try:
                self.rag_fusion = RAGFusion(
                    retriever=self.hybrid_retriever,
                    query_expander=self.query_expander,
                    reranker=self.reranker,
                )
                logger.info("RAG-Fusion initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG-Fusion: {e}")
        
        # 上下文压缩器
        self.context_compressor = None
        if enable_context_compression:
            try:
                from openai import OpenAI
                llm_client = OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL
                ) if settings.OPENAI_API_KEY else None
                self.context_compressor = ContextCompressor(llm_client=llm_client)
                logger.info("Context compressor initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize context compressor: {e}")
        
        # 自适应检索器（需要先初始化基础服务）
        self.adaptive_retriever = None
        if enable_adaptive:
            try:
                # 延迟初始化（需要self作为base_retriever）
                self._adaptive_enabled = True
            except Exception as e:
                logger.warning(f"Failed to enable adaptive retrieval: {e}")
        else:
            self._adaptive_enabled = False
        
        # 多向量检索器
        self.multi_vector_retriever = None
        if enable_multi_vector:
            try:
                # 延迟初始化
                self._multi_vector_enabled = True
            except Exception as e:
                logger.warning(f"Failed to enable multi-vector retrieval: {e}")
        else:
            self._multi_vector_enabled = False
        
        # 缓存配置
        self.enable_caching = enable_caching
        self.cache_dir = Path("./rag_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # BM25索引缓存
        self.bm25_index_cache = None
        self.bm25_cache_path = self.cache_dir / f"bm25_index_{org_id or 'public'}.pkl"
        
        # 金融场景优化
        self.financial_optimized = financial_optimized
        if financial_optimized:
            logger.info("Financial scene optimization enabled")
    
    def _get_cache_key(self, query: str, top_k: int, filter_meta: Optional[Dict]) -> str:
        """生成缓存key"""
        cache_data = {
            "query": query,
            "top_k": top_k,
            "filter_meta": filter_meta or {},
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _load_bm25_index(self) -> Optional[Any]:
        """加载BM25索引缓存"""
        if self.bm25_index_cache is not None:
            return self.bm25_index_cache
        
        if self.bm25_cache_path.exists():
            try:
                with open(self.bm25_cache_path, "rb") as f:
                    self.bm25_index_cache = pickle.load(f)
                logger.info("BM25 index loaded from cache")
                return self.bm25_index_cache
            except Exception as e:
                logger.warning(f"Failed to load BM25 cache: {e}")
        
        return None
    
    def _save_bm25_index(self, index: Any) -> None:
        """保存BM25索引缓存"""
        try:
            with open(self.bm25_cache_path, "wb") as f:
                pickle.dump(index, f)
            self.bm25_index_cache = index
            logger.info("BM25 index saved to cache")
        except Exception as e:
            logger.warning(f"Failed to save BM25 cache: {e}")
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_meta: Optional[Dict] = None,
        use_rag_fusion: bool = False,
        context: Optional[Dict[str, Any]] = None,
        use_adaptive: Optional[bool] = None,  # None = auto
        use_multi_vector: bool = False,
        use_compression: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        高级检索入口
        
        Args:
            query: 查询文本
            top_k: 返回数量
            filter_meta: 元数据过滤
            use_rag_fusion: 是否使用RAG-Fusion（性能开销大）
            context: 上下文信息（用于查询扩展）
            use_adaptive: 是否使用自适应检索（None=自动选择）
            use_multi_vector: 是否使用多向量检索
            use_compression: 是否使用上下文压缩
            
        Returns:
            检索结果列表
        """
        # 检查缓存
        if self.enable_caching:
            cache_key = self._get_cache_key(query, top_k, filter_meta)
            cache_file = self.cache_dir / f"query_{cache_key}.json"
            
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cached_results = json.load(f)
                    logger.info(f"Cache hit for query: {query[:50]}")
                    return cached_results
                except Exception as e:
                    logger.warning(f"Failed to load cache: {e}")
        
        # 自适应检索（如果启用）
        if (use_adaptive is True) or (use_adaptive is None and self._adaptive_enabled):
            if self.adaptive_retriever is None:
                self.adaptive_retriever = AdaptiveRetriever(base_retriever=self)
            
            try:
                results = await self.adaptive_retriever.adaptive_search(
                    query=query,
                    top_k=top_k,
                    context=context,
                    filter_meta=filter_meta,
                )
                
                # 保存缓存
                if self.enable_caching and results:
                    self._save_query_cache(cache_key, results)
                
                return results
            except Exception as e:
                logger.error(f"Adaptive search failed: {e}, falling back")
        
        # 多向量检索
        if use_multi_vector:
            if self.multi_vector_retriever is None:
                self.multi_vector_retriever = MultiVectorRetriever(base_retriever=self)
            
            try:
                results = await self.multi_vector_retriever.multi_vector_search(
                    query=query,
                    top_k=top_k,
                    filter_meta=filter_meta,
                )
                
                if self.enable_caching and results:
                    self._save_query_cache(cache_key, results)
                
                return results
            except Exception as e:
                logger.error(f"Multi-vector search failed: {e}, falling back")
        
        # RAG-Fusion模式（最先进但性能开销大）
        if use_rag_fusion and self.rag_fusion:
            try:
                results = await self.rag_fusion.fused_search(
                    query=query,
                    context=context,
                    top_k=top_k,
                    filter_meta=filter_meta,
                )
                return results
            except Exception as e:
                logger.error(f"RAG-Fusion failed: {e}, falling back to hybrid search")
        
        # 混合检索模式
        if self.hybrid_retriever:
            try:
                # 检查BM25索引是否存在
                if not self.hybrid_retriever.has_bm25:
                    # 尝试构建BM25索引
                    await self.build_and_cache_bm25_index()
                
                # 获取文档列表用于BM25（如果索引不存在）
                documents = None
                if not self.hybrid_retriever.has_bm25:
                    all_docs = self.knowledge_service.list_documents(limit=1000)
                    documents = [doc.get("content", "") for doc in all_docs if doc.get("content")]
                
                results = self.hybrid_retriever.hybrid_search(
                    query=query,
                    documents=documents,  # 如果BM25索引存在，可以为None
                    top_k=top_k * 2,  # 检索更多候选用于rerank
                    filter_meta=filter_meta,
                    use_bm25=self.hybrid_retriever.has_bm25 or bool(documents),
                )
                
                # 应用Reranker
                if self.reranker and results:
                    documents_for_rerank = [r["content"] for r in results]
                    reranked = self.reranker.rerank(
                        query=query,
                        documents=documents_for_rerank,
                        top_k=top_k,
                    )
                    
                    # 合并元数据
                    content_to_meta = {r["content"]: r.get("metadata", {}) for r in results}
                    final_results = []
                    for rerank_result in reranked:
                        content = rerank_result["content"]
                        final_results.append({
                            "content": content,
                            "metadata": content_to_meta.get(content, {}),
                            "rerank_score": rerank_result["score"],
                            "rank": rerank_result["rank"],
                            "source": "hybrid_reranked",
                        })
                    return final_results
                
                return results[:top_k]
                
            except Exception as e:
                logger.error(f"Hybrid search failed: {e}, falling back to vector search")
        
        # 降级：基础向量检索
        results = self.knowledge_service.query(
            text=query,
            top_k=top_k,
            filter_meta=filter_meta,
            min_relevance=0.5,
            rerank=True,
        )
        
        # 上下文压缩（如果启用）
        if use_compression and self.context_compressor and results:
            try:
                documents = [r["content"] for r in results]
                compressed = await self.context_compressor.compress(
                    query=query,
                    documents=documents,
                    max_tokens=300,
                    preserve_financial_data=self.financial_optimized,
                )
                
                for i, comp in enumerate(compressed):
                    if i < len(results):
                        results[i]["content"] = comp["compressed"]
                        results[i]["compression_ratio"] = comp["compression_ratio"]
            except Exception as e:
                logger.warning(f"Context compression failed: {e}")
        
        # 保存缓存
        if self.enable_caching and results:
            self._save_query_cache(cache_key, results)
        
        return results
    
    def _save_query_cache(self, cache_key: str, results: List[Dict]) -> None:
        """保存查询结果缓存"""
        try:
            cache_file = self.cache_dir / f"query_{cache_key}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save query cache: {e}")
    
    async def build_and_cache_bm25_index(self) -> bool:
        """构建并缓存BM25索引"""
        if not self.hybrid_retriever:
            return False
        
        try:
            # 加载所有文档
            all_docs = self.knowledge_service.list_documents(limit=10000)
            documents = [doc.get("content", "") for doc in all_docs if doc.get("content")]
            
            if not documents:
                logger.warning("No documents found for BM25 index")
                return False
            
            # 构建索引
            bm25_index = self.hybrid_retriever.build_bm25_index(documents)
            
            if bm25_index:
                # 保存缓存
                self._save_bm25_index(bm25_index)
                # 设置到retriever
                self.hybrid_retriever.bm25_index = bm25_index
                self.hybrid_retriever.has_bm25 = True
                logger.info(f"BM25 index built and cached: {len(documents)} documents")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            return False

