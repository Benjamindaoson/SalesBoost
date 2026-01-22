"""
RAG 检索性能压力测试脚本
测试检索准确率、响应时间和并发性能
"""
import asyncio
import time
import logging
from typing import List, Dict, Any
from app.services.knowledge_service import KnowledgeService
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGPerformanceTester:
    """RAG 性能测试器"""
    
    def __init__(self):
        self.knowledge_service = KnowledgeService()
        self.test_queries = [
            "信用卡年费是多少？",
            "如何应对客户的价格异议？",
            "产品的主要优势是什么？",
            "客户担心风险怎么办？",
            "如何提高成交率？",
            "客户说考虑一下怎么回复？",
            "产品和其他竞品有什么区别？",
            "如何挖掘客户的真实需求？",
            "客户拒绝购买的原因有哪些？",
            "销售话术有哪些技巧？",
        ]
    
    async def test_single_query(
        self,
        query: str,
        top_k: int = 3,
        min_relevance: float = 0.5,
    ) -> Dict[str, Any]:
        """测试单个查询"""
        start_time = time.time()
        
        try:
            results = self.knowledge_service.query(
                text=query,
                top_k=top_k,
                min_relevance=min_relevance,
                rerank=True,
            )
            
            elapsed = time.time() - start_time
            
            return {
                "query": query,
                "success": True,
                "results_count": len(results),
                "response_time_ms": elapsed * 1000,
                "relevance_scores": [r.get("relevance_score", 0) for r in results],
                "avg_relevance": sum(r.get("relevance_score", 0) for r in results) / len(results) if results else 0,
            }
        except Exception as e:
            return {
                "query": query,
                "success": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
            }
    
    async def test_concurrent_queries(
        self,
        num_concurrent: int = 10,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """测试并发查询性能"""
        queries = self.test_queries[:num_concurrent]
        
        start_time = time.time()
        tasks = [
            self.test_single_query(query, top_k=top_k)
            for query in queries
        ]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        avg_response_time = sum(r["response_time_ms"] for r in successful) / len(successful) if successful else 0
        avg_relevance = sum(r.get("avg_relevance", 0) for r in successful) / len(successful) if successful else 0
        
        return {
            "total_queries": len(queries),
            "successful": len(successful),
            "failed": len(failed),
            "total_time_seconds": total_time,
            "avg_response_time_ms": avg_response_time,
            "queries_per_second": len(queries) / total_time if total_time > 0 else 0,
            "avg_relevance_score": avg_relevance,
            "results": results,
        }
    
    async def test_relevance_accuracy(
        self,
        test_cases: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        测试检索相关性准确性
        
        test_cases: [
            {
                "query": "查询文本",
                "expected_topics": ["期望的主题"],
                "expected_entities": ["期望的实体"],
            },
            ...
        ]
        """
        if not test_cases:
            # 默认测试用例
            test_cases = [
                {
                    "query": "信用卡年费",
                    "expected_keywords": ["年费", "费用", "价格"],
                },
                {
                    "query": "价格异议",
                    "expected_keywords": ["价格", "异议", "反对"],
                },
            ]
        
        accuracy_results = []
        
        for case in test_cases:
            query = case["query"]
            expected_keywords = case.get("expected_keywords", [])
            
            results = self.knowledge_service.query(
                text=query,
                top_k=3,
                min_relevance=0.5,
                rerank=True,
            )
            
            # 检查结果中是否包含期望的关键词
            if results:
                result_text = " ".join([r["content"] for r in results]).lower()
                matched_keywords = [
                    kw for kw in expected_keywords
                    if kw.lower() in result_text
                ]
                
                accuracy = len(matched_keywords) / len(expected_keywords) if expected_keywords else 0
            else:
                accuracy = 0
                matched_keywords = []
            
            accuracy_results.append({
                "query": query,
                "accuracy": accuracy,
                "matched_keywords": matched_keywords,
                "expected_keywords": expected_keywords,
                "has_results": len(results) > 0,
            })
        
        avg_accuracy = sum(r["accuracy"] for r in accuracy_results) / len(accuracy_results) if accuracy_results else 0
        
        return {
            "test_cases": len(test_cases),
            "avg_accuracy": avg_accuracy,
            "results": accuracy_results,
        }
    
    async def run_full_test_suite(self) -> Dict[str, Any]:
        """运行完整测试套件"""
        logger.info("=== Starting RAG Performance Test Suite ===")
        
        # 1. 单查询测试
        logger.info("1. Testing single queries...")
        single_results = []
        for query in self.test_queries[:5]:
            result = await self.test_single_query(query)
            single_results.append(result)
            logger.info(f"  Query: {query[:30]}... | Time: {result['response_time_ms']:.2f}ms | Relevance: {result.get('avg_relevance', 0):.2f}")
        
        # 2. 并发测试
        logger.info("\n2. Testing concurrent queries...")
        concurrent_result = await self.test_concurrent_queries(num_concurrent=10)
        logger.info(f"  Total: {concurrent_result['total_queries']} queries")
        logger.info(f"  Successful: {concurrent_result['successful']}")
        logger.info(f"  Avg Response Time: {concurrent_result['avg_response_time_ms']:.2f}ms")
        logger.info(f"  Queries/Second: {concurrent_result['queries_per_second']:.2f}")
        logger.info(f"  Avg Relevance: {concurrent_result['avg_relevance_score']:.2f}")
        
        # 3. 相关性准确性测试
        logger.info("\n3. Testing relevance accuracy...")
        accuracy_result = await self.test_relevance_accuracy()
        logger.info(f"  Test Cases: {accuracy_result['test_cases']}")
        logger.info(f"  Avg Accuracy: {accuracy_result['avg_accuracy']:.2%}")
        
        # 汇总报告
        report = {
            "timestamp": time.time(),
            "single_query_tests": {
                "count": len(single_results),
                "avg_response_time_ms": sum(r["response_time_ms"] for r in single_results) / len(single_results),
                "avg_relevance": sum(r.get("avg_relevance", 0) for r in single_results) / len(single_results),
            },
            "concurrent_tests": concurrent_result,
            "accuracy_tests": accuracy_result,
            "recommendations": self._generate_recommendations(
                single_results,
                concurrent_result,
                accuracy_result,
            ),
        }
        
        logger.info("\n=== Test Suite Completed ===")
        logger.info(f"Recommendations: {report['recommendations']}")
        
        return report
    
    def _generate_recommendations(
        self,
        single_results: List[Dict],
        concurrent_result: Dict,
        accuracy_result: Dict,
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 响应时间建议
        avg_time = concurrent_result.get("avg_response_time_ms", 0)
        if avg_time > 500:
            recommendations.append("响应时间较慢，考虑优化向量检索或增加缓存")
        elif avg_time > 200:
            recommendations.append("响应时间可接受，但仍有优化空间")
        else:
            recommendations.append("响应时间良好")
        
        # 相关性建议
        avg_relevance = concurrent_result.get("avg_relevance_score", 0)
        if avg_relevance < 0.6:
            recommendations.append("相关性分数较低，建议优化embedding模型或增加训练数据")
        elif avg_relevance < 0.75:
            recommendations.append("相关性可接受，建议微调检索参数")
        else:
            recommendations.append("相关性良好")
        
        # 准确性建议
        accuracy = accuracy_result.get("avg_accuracy", 0)
        if accuracy < 0.7:
            recommendations.append("检索准确性需要提升，检查知识库内容和查询策略")
        elif accuracy < 0.85:
            recommendations.append("检索准确性良好，可进一步优化")
        else:
            recommendations.append("检索准确性优秀")
        
        return recommendations


async def main():
    """主函数"""
    tester = RAGPerformanceTester()
    report = await tester.run_full_test_suite()
    
    # 打印详细报告
    print("\n" + "="*60)
    print("RAG Performance Test Report")
    print("="*60)
    print(f"\nSingle Query Performance:")
    print(f"  Average Response Time: {report['single_query_tests']['avg_response_time_ms']:.2f}ms")
    print(f"  Average Relevance: {report['single_query_tests']['avg_relevance']:.2f}")
    
    print(f"\nConcurrent Performance:")
    print(f"  Queries/Second: {report['concurrent_tests']['queries_per_second']:.2f}")
    print(f"  Success Rate: {report['concurrent_tests']['successful']}/{report['concurrent_tests']['total_queries']}")
    
    print(f"\nAccuracy:")
    print(f"  Average Accuracy: {report['accuracy_tests']['avg_accuracy']:.2%}")
    
    print(f"\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  - {rec}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())



