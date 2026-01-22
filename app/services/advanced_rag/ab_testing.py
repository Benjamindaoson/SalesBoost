"""
A/B测试框架 - RAG检索策略对比
支持不同检索策略的效果对比和参数调优
"""
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ABTestFramework:
    """
    A/B测试框架
    
    功能：
    - 对比不同检索策略
    - 参数调优
    - 效果追踪和报告
    """
    
    def __init__(self, results_dir: str = "./ab_test_results"):
        """
        初始化A/B测试框架
        
        Args:
            results_dir: 结果保存目录
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        self.test_results = []
    
    async def compare_strategies(
        self,
        query: str,
        strategies: List[Dict[str, Any]],
        ground_truth: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        对比不同检索策略
        
        Args:
            query: 测试查询
            strategies: 策略列表，每个策略包含：
                {
                    "name": str,
                    "retriever": AdvancedRAGService实例,
                    "config": {...},  # 检索配置
                }
            ground_truth: 正确答案（可选）
            
        Returns:
            对比结果
        """
        from app.services.advanced_rag.evaluation_metrics import RetrievalMetrics
        
        comparison_results = {
            "query": query,
            "timestamp": datetime.utcnow().isoformat(),
            "strategies": [],
        }
        
        for strategy in strategies:
            strategy_name = strategy["name"]
            retriever = strategy["retriever"]
            config = strategy.get("config", {})
            
            try:
                # 执行检索
                results = await retriever.search(query=query, **config)
                
                # 计算指标
                metrics = {}
                if ground_truth:
                    metrics = {
                        "mrr": RetrievalMetrics.calculate_mrr(results, ground_truth),
                        "ndcg@5": RetrievalMetrics.calculate_ndcg(results, ground_truth, k=5),
                        "precision@5": RetrievalMetrics.calculate_precision_at_k(results, ground_truth, k=5),
                        "recall@5": RetrievalMetrics.calculate_recall_at_k(results, ground_truth, k=5),
                    }
                
                # 金融场景准确率
                financial_accuracy = RetrievalMetrics.calculate_financial_accuracy(results, query)
                
                strategy_result = {
                    "name": strategy_name,
                    "config": config,
                    "results_count": len(results),
                    "metrics": metrics,
                    "financial_accuracy": financial_accuracy,
                    "top_results": [
                        {
                            "content": r.get("content", "")[:100],
                            "score": r.get("rerank_score", r.get("relevance_score", 0)),
                        }
                        for r in results[:3]
                    ],
                }
                
                comparison_results["strategies"].append(strategy_result)
                
            except Exception as e:
                logger.error(f"Strategy {strategy_name} failed: {e}")
                comparison_results["strategies"].append({
                    "name": strategy_name,
                    "error": str(e),
                })
        
        # 保存结果
        self._save_comparison_result(comparison_results)
        
        return comparison_results
    
    def _save_comparison_result(self, result: Dict[str, Any]) -> None:
        """保存对比结果"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"comparison_{timestamp}.json"
            filepath = self.results_dir / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Comparison result saved: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save comparison result: {e}")
    
    async def parameter_tuning(
        self,
        query: str,
        base_retriever,
        parameter_space: Dict[str, List[Any]],
        ground_truth: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        参数调优
        
        Args:
            query: 测试查询
            base_retriever: 基础检索器
            parameter_space: 参数空间，例如：
                {
                    "top_k": [3, 5, 10],
                    "min_relevance": [0.5, 0.6, 0.7],
                }
            ground_truth: 正确答案
            
        Returns:
            最优参数配置
        """
        from itertools import product
        from app.services.advanced_rag.evaluation_metrics import RetrievalMetrics
        
        best_config = None
        best_score = 0.0
        all_results = []
        
        # 生成所有参数组合
        param_names = list(parameter_space.keys())
        param_values = list(parameter_space.values())
        
        for param_combo in product(*param_values):
            config = dict(zip(param_names, param_combo))
            
            try:
                # 执行检索
                results = await base_retriever.search(query=query, **config)
                
                # 计算分数（使用NDCG@5）
                if ground_truth:
                    score = RetrievalMetrics.calculate_ndcg(results, ground_truth, k=5)
                else:
                    # 如果没有ground_truth，使用平均相关性分数
                    scores = [r.get("rerank_score", r.get("relevance_score", 0)) for r in results]
                    score = sum(scores) / len(scores) if scores else 0.0
                
                all_results.append({
                    "config": config,
                    "score": score,
                    "results_count": len(results),
                })
                
                # 更新最优配置
                if score > best_score:
                    best_score = score
                    best_config = config
                    
            except Exception as e:
                logger.warning(f"Parameter tuning failed for {config}: {e}")
        
        tuning_result = {
            "query": query,
            "parameter_space": parameter_space,
            "best_config": best_config,
            "best_score": best_score,
            "all_results": all_results,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # 保存调优结果
        self._save_tuning_result(tuning_result)
        
        return tuning_result
    
    def _save_tuning_result(self, result: Dict[str, Any]) -> None:
        """保存调优结果"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"tuning_{timestamp}.json"
            filepath = self.results_dir / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Tuning result saved: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save tuning result: {e}")
    
    def generate_report(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成测试报告
        
        Args:
            test_cases: 测试用例列表
            
        Returns:
            测试报告
        """
        report = {
            "total_tests": len(test_cases),
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {},
            "detailed_results": test_cases,
        }
        
        # 计算汇总统计
        if test_cases:
            all_mrrs = []
            all_ndcgs = []
            all_precisions = []
            
            for case in test_cases:
                strategies = case.get("strategies", [])
                for strategy in strategies:
                    metrics = strategy.get("metrics", {})
                    if "mrr" in metrics:
                        all_mrrs.append(metrics["mrr"])
                    if "ndcg@5" in metrics:
                        all_ndcgs.append(metrics["ndcg@5"])
                    if "precision@5" in metrics:
                        all_precisions.append(metrics["precision@5"])
            
            if all_mrrs:
                report["summary"]["avg_mrr"] = sum(all_mrrs) / len(all_mrrs)
            if all_ndcgs:
                report["summary"]["avg_ndcg@5"] = sum(all_ndcgs) / len(all_ndcgs)
            if all_precisions:
                report["summary"]["avg_precision@5"] = sum(all_precisions) / len(all_precisions)
        
        # 保存报告
        self._save_report(report)
        
        return report
    
    def _save_report(self, report: Dict[str, Any]) -> None:
        """保存测试报告"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.json"
            filepath = self.results_dir / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Test report saved: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")



