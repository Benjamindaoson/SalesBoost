"""
多向量检索器 - Multi-Vector Retrieval
层次化检索：父文档检索 + 子块检索
针对金融长文档优化（产品说明书、合同条款等）
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MultiVectorRetriever:
    """
    多向量检索器
    
    策略：
    1. 父文档检索（粗筛）：找到相关文档
    2. 子块检索（精筛）：在相关文档内检索具体片段
    3. 结果合并：结合文档级和块级信息
    """
    
    def __init__(self, base_retriever):
        """
        初始化多向量检索器
        
        Args:
            base_retriever: 基础检索器（AdvancedRAGService实例）
        """
        self.base_retriever = base_retriever
    
    async def multi_vector_search(
        self,
        query: str,
        top_k: int = 5,
        parent_top_k: int = 10,  # 父文档检索数量
        child_top_k: int = 3,    # 每个父文档的子块数量
        filter_meta: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        多向量检索
        
        Args:
            query: 查询文本
            top_k: 最终返回数量
            parent_top_k: 父文档检索数量
            child_top_k: 每个父文档的子块数量
            filter_meta: 元数据过滤
            
        Returns:
            检索结果（包含父文档和子块信息）
        """
        # Step 1: 父文档检索（文档级，非chunk）
        parent_filter = {
            **(filter_meta or {}),
            "is_chunk": False,  # 只检索父文档
        }
        
        parent_results = await self.base_retriever.search(
            query=query,
            top_k=parent_top_k,
            filter_meta=parent_filter,
            use_rag_fusion=False,
        )
        
        logger.info(f"Multi-vector: Found {len(parent_results)} parent documents")
        
        # Step 2: 对每个父文档，检索其子块
        all_child_results = []
        parent_doc_ids = set()
        
        for parent_result in parent_results:
            parent_doc_id = parent_result.get("metadata", {}).get("parent_doc_id") or \
                           parent_result.get("metadata", {}).get("doc_id")
            
            if not parent_doc_id:
                # 如果没有parent_doc_id，尝试从id推断
                doc_id = parent_result.get("metadata", {}).get("id", "")
                parent_doc_id = doc_id.split("_")[0] if "_" in doc_id else doc_id
            
            if parent_doc_id and parent_doc_id not in parent_doc_ids:
                parent_doc_ids.add(parent_doc_id)
                
                # 检索该父文档的子块
                child_filter = {
                    **(filter_meta or {}),
                    "parent_doc_id": parent_doc_id,
                    "is_chunk": True,
                }
                
                child_results = await self.base_retriever.search(
                    query=query,
                    top_k=child_top_k,
                    filter_meta=child_filter,
                    use_rag_fusion=False,
                )
                
                # 为每个子块添加父文档信息
                for child_result in child_results:
                    child_result["parent_document"] = {
                        "id": parent_doc_id,
                        "content": parent_result.get("content", "")[:200],  # 父文档摘要
                        "metadata": parent_result.get("metadata", {}),
                    }
                    child_result["parent_relevance"] = parent_result.get(
                        "rerank_score",
                        parent_result.get("relevance_score", 0)
                    )
                
                all_child_results.extend(child_results)
        
        # Step 3: 合并和排序
        # 综合分数 = 父文档相关性 * 0.3 + 子块相关性 * 0.7
        for result in all_child_results:
            child_score = result.get("rerank_score", result.get("relevance_score", 0))
            parent_score = result.get("parent_relevance", 0)
            result["combined_score"] = parent_score * 0.3 + child_score * 0.7
        
        # 按综合分数排序
        all_child_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        # Step 4: 去重（同一父文档的多个子块）
        final_results = self._deduplicate_by_parent(all_child_results, top_k)
        
        logger.info(f"Multi-vector: Returning {len(final_results)} results")
        
        return final_results
    
    def _deduplicate_by_parent(
        self,
        results: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """按父文档去重，每个父文档最多保留N个子块"""
        parent_counts = {}  # {parent_id: count}
        final_results = []
        
        for result in results:
            parent_id = result.get("parent_document", {}).get("id")
            
            if not parent_id:
                # 如果没有父文档信息，直接添加
                final_results.append(result)
                continue
            
            # 检查该父文档是否已有足够的子块
            count = parent_counts.get(parent_id, 0)
            max_per_parent = 2  # 每个父文档最多2个子块
            
            if count < max_per_parent:
                final_results.append(result)
                parent_counts[parent_id] = count + 1
                
                if len(final_results) >= top_k:
                    break
        
        return final_results[:top_k]
    
    async def hierarchical_search(
        self,
        query: str,
        top_k: int = 5,
        filter_meta: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        层次化检索（返回文档级和块级结果）
        
        Returns:
            {
                "parent_documents": [...],  # 文档级结果
                "child_chunks": [...],      # 块级结果
                "combined": [...],          # 合并结果
            }
        """
        # 父文档检索
        parent_filter = {
            **(filter_meta or {}),
            "is_chunk": False,
        }
        parent_results = await self.base_retriever.search(
            query=query,
            top_k=top_k,
            filter_meta=parent_filter,
        )
        
        # 子块检索
        child_filter = {
            **(filter_meta or {}),
            "is_chunk": True,
        }
        child_results = await self.base_retriever.search(
            query=query,
            top_k=top_k * 2,
            filter_meta=child_filter,
        )
        
        # 合并结果
        combined = await self.multi_vector_search(
            query=query,
            top_k=top_k,
            filter_meta=filter_meta,
        )
        
        return {
            "parent_documents": parent_results,
            "child_chunks": child_results,
            "combined": combined,
        }


