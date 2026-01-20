"""
专业Reranker - Cross-Encoder Reranking
使用BGE-Reranker或Cohere Rerank进行精确重排序
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# 尝试导入BGE-Reranker
try:
    from FlagEmbedding import FlagReranker
    HAS_BGE_RERANKER = True
except ImportError:
    HAS_BGE_RERANKER = False
    logger.warning("FlagEmbedding not installed. BGE-Reranker disabled. Install with: pip install FlagEmbedding")

# 尝试导入Cohere
try:
    import cohere
    HAS_COHERE = True
except ImportError:
    HAS_COHERE = False


class Reranker:
    """
    专业Reranker
    
    支持多种Reranker模型：
    - BGE-Reranker（开源，推荐）
    - Cohere Rerank v3（API，准确率最高）
    """
    
    def __init__(
        self,
        model_type: str = "bge",  # "bge" or "cohere"
        model_name: str = "BAAI/bge-reranker-base",
        cohere_api_key: Optional[str] = None,
    ):
        """
        初始化Reranker
        
        Args:
            model_type: 模型类型 ("bge" or "cohere")
            model_name: BGE模型名称
            cohere_api_key: Cohere API密钥（如果使用Cohere）
        """
        self.model_type = model_type
        self.reranker = None
        self.cohere_client = None
        
        if model_type == "bge":
            if HAS_BGE_RERANKER:
                try:
                    self.reranker = FlagReranker(model_name, use_fp16=True)
                    logger.info(f"BGE-Reranker loaded: {model_name}")
                except Exception as e:
                    logger.error(f"Failed to load BGE-Reranker: {e}")
                    self.reranker = None
            else:
                logger.warning("BGE-Reranker not available, falling back to simple reranking")
        
        elif model_type == "cohere":
            if HAS_COHERE and cohere_api_key:
                try:
                    self.cohere_client = cohere.Client(api_key=cohere_api_key)
                    logger.info("Cohere Rerank client initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize Cohere client: {e}")
            else:
                logger.warning("Cohere not available or API key missing")
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        重排序文档
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回top_k结果（如果为None则返回全部）
            
        Returns:
            重排序后的结果，包含score和rank
        """
        if not documents:
            return []
        
        # 如果只有一个文档，直接返回
        if len(documents) == 1:
            return [{
                "content": documents[0],
                "score": 1.0,
                "rank": 1,
            }]
        
        try:
            if self.model_type == "bge" and self.reranker:
                return self._rerank_bge(query, documents, top_k)
            elif self.model_type == "cohere" and self.cohere_client:
                return self._rerank_cohere(query, documents, top_k)
            else:
                # 降级：简单基于关键词的排序
                return self._rerank_fallback(query, documents, top_k)
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return self._rerank_fallback(query, documents, top_k)
    
    def _rerank_bge(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int],
    ) -> List[Dict[str, Any]]:
        """使用BGE-Reranker重排序"""
        # 构建query-document对
        pairs = [[query, doc] for doc in documents]
        
        # 计算相关性分数
        scores = self.reranker.compute_score(pairs)
        
        # 处理分数（可能是单个值或列表）
        if isinstance(scores, float):
            scores = [scores]
        elif len(scores) == 1:
            scores = scores[0] if isinstance(scores[0], list) else scores
        
        # 排序
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # 格式化结果
        results = []
        for rank, (doc, score) in enumerate(scored_docs, 1):
            if top_k and rank > top_k:
                break
            results.append({
                "content": doc,
                "score": float(score),
                "rank": rank,
            })
        
        return results
    
    def _rerank_cohere(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int],
    ) -> List[Dict[str, Any]]:
        """使用Cohere Rerank v3重排序"""
        try:
            response = self.cohere_client.rerank(
                model="rerank-multilingual-v3.0",  # 支持中文
                query=query,
                documents=documents,
                top_n=top_k or len(documents),
            )
            
            results = []
            for idx, result in enumerate(response.results, 1):
                results.append({
                    "content": documents[result.index],
                    "score": float(result.relevance_score),
                    "rank": idx,
                })
            
            return results
        except Exception as e:
            logger.error(f"Cohere reranking failed: {e}")
            return self._rerank_fallback(query, documents, top_k)
    
    def _rerank_fallback(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int],
    ) -> List[Dict[str, Any]]:
        """降级方案：基于关键词匹配的简单排序"""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_docs = []
        for doc in documents:
            doc_lower = doc.lower()
            doc_words = set(doc_lower.split())
            
            # 计算关键词重叠率
            overlap = len(query_words & doc_words) / max(len(query_words), 1)
            scored_docs.append((doc, overlap))
        
        # 排序
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # 格式化结果
        results = []
        for rank, (doc, score) in enumerate(scored_docs, 1):
            if top_k and rank > top_k:
                break
            results.append({
                "content": doc,
                "score": float(score),
                "rank": rank,
            })
        
        return results


