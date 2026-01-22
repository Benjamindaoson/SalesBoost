"""
混合检索器 - Hybrid Search (Vector + BM25)
2026年最先进的混合检索实现
"""
import logging
from typing import List, Dict, Any, Optional
import math

logger = logging.getLogger(__name__)

# 尝试导入BM25
try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False
    logger.warning("rank-bm25 not installed. BM25 search will be disabled. Install with: pip install rank-bm25")


class HybridRetriever:
    """
    混合检索器
    
    结合向量检索和BM25关键词检索，使用Reciprocal Rank Fusion (RRF)融合结果
    """
    
    def __init__(self, vector_collection, bm25_index: Optional[BM25Okapi] = None):
        """
        初始化混合检索器
        
        Args:
            vector_collection: ChromaDB集合（向量检索）
            bm25_index: BM25索引（关键词检索，可选）
        """
        self.vector_collection = vector_collection
        self.bm25_index = bm25_index
        self.has_bm25 = HAS_BM25 and bm25_index is not None
        
        # RRF参数（Reciprocal Rank Fusion）
        self.rrf_k = 60  # RRF常数，通常60-100
        
        # 混合权重
        self.vector_weight = 0.7  # 向量检索权重
        self.bm25_weight = 0.3   # BM25检索权重
    
    def build_bm25_index(self, documents: List[str]) -> Optional[BM25Okapi]:
        """
        构建BM25索引
        
        Args:
            documents: 文档列表
            
        Returns:
            BM25索引对象
        """
        if not HAS_BM25:
            logger.warning("rank-bm25 not available, skipping BM25 index building")
            return None
        
        try:
            # 中文分词（简单实现，生产环境建议使用jieba）
            tokenized_docs = [self._tokenize(doc) for doc in documents]
            bm25 = BM25Okapi(tokenized_docs)
            logger.info(f"BM25 index built with {len(documents)} documents")
            return bm25
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            return None
    
    def _tokenize(self, text: str) -> List[str]:
        """
        简单的中文分词（生产环境建议使用jieba）
        
        Args:
            text: 文本
            
        Returns:
            词列表
        """
        # 简单实现：按字符和常见分隔符分割
        import re
        # 保留中文、英文、数字
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+|\d+', text)
        return tokens if tokens else [text]
    
    def vector_search(
        self,
        query: str,
        top_k: int = 20,
        filter_meta: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量检索
        
        Returns:
            [{"content": str, "metadata": dict, "distance": float, "rank": int}, ...]
        """
        try:
            results = self.vector_collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filter_meta
            )
            
            formatted = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 1.0,
                        "rank": i + 1,
                        "source": "vector",
                    })
            
            return formatted
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def bm25_search(
        self,
        query: str,
        documents: List[str],
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        BM25关键词检索
        
        Args:
            query: 查询文本
            documents: 文档列表（需要与BM25索引对应）
            top_k: 返回数量
            
        Returns:
            [{"content": str, "score": float, "rank": int}, ...]
        """
        if not self.has_bm25 or not self.bm25_index:
            return []
        
        try:
            tokenized_query = self._tokenize(query)
            scores = self.bm25_index.get_scores(tokenized_query)
            
            # 获取top_k结果
            top_indices = sorted(
                range(len(scores)),
                key=lambda i: scores[i],
                reverse=True
            )[:top_k]
            
            results = []
            for rank, idx in enumerate(top_indices, 1):
                if scores[idx] > 0:  # 只返回有分数的结果
                    results.append({
                        "content": documents[idx],
                        "score": float(scores[idx]),
                        "rank": rank,
                        "source": "bm25",
                    })
            
            return results
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []
    
    def reciprocal_rank_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF) 融合算法
        
        公式: RRF(d) = sum(1 / (k + rank(d, i))) for each retrieval method i
        
        Args:
            vector_results: 向量检索结果
            bm25_results: BM25检索结果
            top_k: 最终返回数量
            
        Returns:
            融合后的排序结果
        """
        # 构建文档ID到RRF分数的映射
        doc_scores = {}  # {content: rrf_score}
        doc_metadata = {}  # {content: metadata}
        
        # 处理向量检索结果
        for result in vector_results:
            content = result["content"]
            rank = result["rank"]
            rrf_score = 1.0 / (self.rrf_k + rank)
            
            if content not in doc_scores:
                doc_scores[content] = 0
                doc_metadata[content] = result.get("metadata", {})
            
            doc_scores[content] += self.vector_weight * rrf_score
        
        # 处理BM25检索结果
        for result in bm25_results:
            content = result["content"]
            rank = result["rank"]
            rrf_score = 1.0 / (self.rrf_k + rank)
            
            if content not in doc_scores:
                doc_scores[content] = 0
                doc_metadata[content] = {}
            
            doc_scores[content] += self.bm25_weight * rrf_score
        
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
                "source": "hybrid",
            })
        
        return fused_results
    
    def hybrid_search(
        self,
        query: str,
        documents: Optional[List[str]] = None,
        top_k: int = 10,
        filter_meta: Optional[Dict] = None,
        use_bm25: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        混合检索主入口
        
        Args:
            query: 查询文本
            documents: 文档列表（用于BM25，如果为None则跳过BM25）
            top_k: 返回数量
            filter_meta: 元数据过滤（仅用于向量检索）
            use_bm25: 是否使用BM25
            
        Returns:
            融合后的检索结果
        """
        # 向量检索（总是执行）
        vector_results = self.vector_search(
            query=query,
            top_k=top_k * 2,  # 检索更多候选用于融合
            filter_meta=filter_meta,
        )
        
        # BM25检索（如果启用且有文档）
        bm25_results = []
        if use_bm25 and self.has_bm25 and documents:
            bm25_results = self.bm25_search(
                query=query,
                documents=documents,
                top_k=top_k * 2,
            )
        
        # 如果只有向量检索，直接返回
        if not bm25_results:
            return vector_results[:top_k]
        
        # RRF融合
        fused_results = self.reciprocal_rank_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            top_k=top_k,
        )
        
        logger.info(
            f"Hybrid search: vector={len(vector_results)}, "
            f"bm25={len(bm25_results)}, fused={len(fused_results)}"
        )
        
        return fused_results



