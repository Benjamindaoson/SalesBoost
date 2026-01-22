"""
检索质量评估指标
MRR, NDCG, Precision@K, Recall@K
针对金融场景的评估指标
"""
import logging
from typing import List, Dict, Any, Optional
import math

logger = logging.getLogger(__name__)


class RetrievalMetrics:
    """检索质量评估指标"""
    
    @staticmethod
    def calculate_mrr(results: List[Dict], ground_truth: List[str]) -> float:
        """
        计算MRR (Mean Reciprocal Rank)
        
        Args:
            results: 检索结果列表
            ground_truth: 正确答案的文档ID列表
            
        Returns:
            MRR分数 (0-1)
        """
        if not ground_truth:
            return 0.0
        
        for rank, result in enumerate(results, 1):
            doc_id = result.get("metadata", {}).get("id") or result.get("id")
            if doc_id in ground_truth:
                return 1.0 / rank
        
        return 0.0
    
    @staticmethod
    def calculate_ndcg(
        results: List[Dict],
        ground_truth: List[str],
        k: int = 5,
    ) -> float:
        """
        计算NDCG@K (Normalized Discounted Cumulative Gain)
        
        Args:
            results: 检索结果列表
            ground_truth: 正确答案的文档ID列表（带相关性分数）
            k: Top K
            
        Returns:
            NDCG@K分数 (0-1)
        """
        if not ground_truth:
            return 0.0
        
        # 计算DCG
        dcg = 0.0
        for rank, result in enumerate(results[:k], 1):
            doc_id = result.get("metadata", {}).get("id") or result.get("id")
            
            # 获取相关性分数（如果ground_truth是dict）
            if isinstance(ground_truth, dict):
                relevance = ground_truth.get(doc_id, 0)
            else:
                relevance = 1.0 if doc_id in ground_truth else 0.0
            
            dcg += relevance / math.log2(rank + 1)
        
        # 计算IDCG（理想DCG）
        ideal_relevances = []
        if isinstance(ground_truth, dict):
            ideal_relevances = sorted(ground_truth.values(), reverse=True)[:k]
        else:
            ideal_relevances = [1.0] * min(len(ground_truth), k)
        
        idcg = sum(rel / math.log2(rank + 1) for rank, rel in enumerate(ideal_relevances, 1))
        
        # NDCG
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    @staticmethod
    def calculate_precision_at_k(
        results: List[Dict],
        ground_truth: List[str],
        k: int = 5,
    ) -> float:
        """
        计算Precision@K
        
        Args:
            results: 检索结果列表
            ground_truth: 正确答案的文档ID列表
            k: Top K
            
        Returns:
            Precision@K分数 (0-1)
        """
        if not ground_truth:
            return 0.0
        
        relevant_count = 0
        for result in results[:k]:
            doc_id = result.get("metadata", {}).get("id") or result.get("id")
            if doc_id in ground_truth:
                relevant_count += 1
        
        return relevant_count / k if k > 0 else 0.0
    
    @staticmethod
    def calculate_recall_at_k(
        results: List[Dict],
        ground_truth: List[str],
        k: int = 5,
    ) -> float:
        """
        计算Recall@K
        
        Args:
            results: 检索结果列表
            ground_truth: 正确答案的文档ID列表
            k: Top K
            
        Returns:
            Recall@K分数 (0-1)
        """
        if not ground_truth:
            return 0.0
        
        relevant_count = 0
        for result in results[:k]:
            doc_id = result.get("metadata", {}).get("id") or result.get("id")
            if doc_id in ground_truth:
                relevant_count += 1
        
        return relevant_count / len(ground_truth) if ground_truth else 0.0
    
    @staticmethod
    def calculate_financial_accuracy(
        results: List[Dict],
        query: str,
    ) -> float:
        """
        计算金融场景准确率
        检查检索结果是否包含关键金融信息（费率、年费等）
        
        Args:
            results: 检索结果列表
            query: 查询文本
            
        Returns:
            金融准确率 (0-1)
        """
        from app.services.advanced_rag.context_compressor import ContextCompressor
        
        compressor = ContextCompressor()
        query_entities = compressor.extract_financial_entities(query)
        
        # 如果查询中没有金融实体，返回0.5（中性）
        if not any(query_entities.values()):
            return 0.5
        
        # 检查结果中是否包含这些实体
        found_entities = {key: [] for key in query_entities.keys()}
        
        for result in results:
            content = result.get("content", "")
            result_entities = compressor.extract_financial_entities(content)
            
            for key in query_entities.keys():
                if query_entities[key] and result_entities[key]:
                    # 检查是否有重叠
                    overlap = set(query_entities[key]) & set(result_entities[key])
                    if overlap:
                        found_entities[key].extend(list(overlap))
        
        # 计算覆盖率
        total_expected = sum(len(v) for v in query_entities.values())
        total_found = sum(len(set(v)) for v in found_entities.values())
        
        if total_expected == 0:
            return 0.5
        
        return min(1.0, total_found / total_expected)
    
    @staticmethod
    def evaluate_batch(
        test_cases: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        批量评估
        
        Args:
            test_cases: [
                {
                    "query": str,
                    "results": List[Dict],
                    "ground_truth": List[str],
                },
                ...
            ]
            
        Returns:
            平均指标
        """
        metrics = {
            "mrr": [],
            "ndcg@5": [],
            "precision@5": [],
            "recall@5": [],
            "financial_accuracy": [],
        }
        
        for case in test_cases:
            query = case.get("query", "")
            results = case.get("results", [])
            ground_truth = case.get("ground_truth", [])
            
            metrics["mrr"].append(
                RetrievalMetrics.calculate_mrr(results, ground_truth)
            )
            metrics["ndcg@5"].append(
                RetrievalMetrics.calculate_ndcg(results, ground_truth, k=5)
            )
            metrics["precision@5"].append(
                RetrievalMetrics.calculate_precision_at_k(results, ground_truth, k=5)
            )
            metrics["recall@5"].append(
                RetrievalMetrics.calculate_recall_at_k(results, ground_truth, k=5)
            )
            metrics["financial_accuracy"].append(
                RetrievalMetrics.calculate_financial_accuracy(results, query)
            )
        
        # 计算平均值
        avg_metrics = {
            key: sum(values) / len(values) if values else 0.0
            for key, values in metrics.items()
        }
        
        return avg_metrics



