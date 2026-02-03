#!/usr/bin/env python3
"""
Semantic Search Quality Validation
Test semantic retrieval accuracy and performance

Test Categories:
1. Synonym tests - Semantic understanding without keyword matching
2. Sales scenario tests - Domain-specific retrieval
3. Performance benchmarks - Latency and accuracy metrics

Performance Requirements:
- Single query latency: <50ms
- Retrieval accuracy: >85%

Author: Claude Sonnet 4.5
Date: 2026-02-01
Priority: P0
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the semantic search engine
from scripts.fix_semantic_search import SimpleVectorStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class SemanticQualityValidator:
    """
    Validate semantic search quality

    Features:
    - Synonym understanding tests
    - Sales scenario relevance tests
    - Performance benchmarking
    - Accuracy scoring
    """

    def __init__(self, vector_store: SimpleVectorStore):
        self.store = vector_store
        self.test_results = []

    def test_synonym_understanding(self) -> Dict[str, Any]:
        """
        Test 1: Synonym Understanding
        Verify semantic retrieval without exact keyword matching
        """
        logger.info("\n=== Test 1: Synonym Understanding ===")

        test_cases = [
            {
                "query": "太贵了",
                "expected_keywords": ["价格", "成本", "费用", "便宜", "优惠"],
                "description": "Price objection - should retrieve price-related content"
            },
            {
                "query": "我再想想",
                "expected_keywords": ["犹豫", "考虑", "决策", "临门一脚", "促成"],
                "description": "Hesitation - should retrieve closing techniques"
            },
            {
                "query": "有什么好处",
                "expected_keywords": ["权益", "优惠", "福利", "价值", "收益"],
                "description": "Benefits inquiry - should retrieve value propositions"
            },
            {
                "query": "和别的卡比怎么样",
                "expected_keywords": ["竞品", "对比", "优势", "差异化"],
                "description": "Competitor comparison - should retrieve competitive advantages"
            }
        ]

        results = []
        total_passed = 0

        for i, test_case in enumerate(test_cases, 1):
            query = test_case["query"]
            expected_keywords = test_case["expected_keywords"]
            description = test_case["description"]

            logger.info(f"\nTest Case {i}: {description}")
            logger.info(f"Query: '{query}'")

            # Perform search
            start_time = time.time()
            search_results = self.store.search(query, top_k=5, min_score=0.3)
            query_time = (time.time() - start_time) * 1000  # Convert to ms

            # Check if any expected keywords appear in results
            found_keywords = []
            for result in search_results:
                text = result['text'].lower()
                for keyword in expected_keywords:
                    if keyword in text:
                        found_keywords.append(keyword)

            found_keywords = list(set(found_keywords))  # Remove duplicates

            # Calculate relevance score
            relevance_score = len(found_keywords) / len(expected_keywords) if expected_keywords else 0

            # Check if query keyword is NOT in top result (true semantic understanding)
            top_result_text = search_results[0]['text'].lower() if search_results else ""
            semantic_match = query.lower() not in top_result_text

            passed = relevance_score >= 0.4 and len(search_results) > 0
            if passed:
                total_passed += 1

            result = {
                "test_case": i,
                "query": query,
                "description": description,
                "num_results": len(search_results),
                "top_score": search_results[0]['score'] if search_results else 0,
                "query_time_ms": query_time,
                "found_keywords": found_keywords,
                "relevance_score": relevance_score,
                "semantic_match": semantic_match,
                "passed": passed
            }
            results.append(result)

            logger.info(f"  Results: {len(search_results)}")
            logger.info(f"  Top score: {result['top_score']:.4f}")
            logger.info(f"  Query time: {query_time:.2f}ms")
            logger.info(f"  Found keywords: {found_keywords}")
            logger.info(f"  Relevance: {relevance_score*100:.1f}%")
            logger.info(f"  Semantic match: {'✓' if semantic_match else '✗'}")
            logger.info(f"  Status: {'PASS' if passed else 'FAIL'}")

            if search_results:
                logger.info(f"  Top result preview: {search_results[0]['text'][:100]}...")

        accuracy = total_passed / len(test_cases) * 100

        summary = {
            "test_name": "Synonym Understanding",
            "total_cases": len(test_cases),
            "passed": total_passed,
            "failed": len(test_cases) - total_passed,
            "accuracy": accuracy,
            "results": results
        }

        logger.info(f"\n[Summary] Synonym Understanding: {total_passed}/{len(test_cases)} passed ({accuracy:.1f}%)")

        return summary

    def test_sales_scenarios(self) -> Dict[str, Any]:
        """
        Test 2: Sales Scenario Relevance
        Verify domain-specific retrieval for sales situations
        """
        logger.info("\n=== Test 2: Sales Scenario Relevance ===")

        test_cases = [
            {
                "query": "年费问题",
                "expected_type": ["champion_case", "training_scenario", "sales_sop"],
                "expected_content": ["年费", "免年费", "刷卡", "次数"],
                "description": "Annual fee objection handling"
            },
            {
                "query": "权益不够用",
                "expected_type": ["champion_case", "training_scenario"],
                "expected_content": ["权益", "价值", "福利", "优惠"],
                "description": "Benefits value packaging"
            },
            {
                "query": "客户说要考虑",
                "expected_type": ["champion_case", "training_scenario"],
                "expected_content": ["犹豫", "促成", "临门", "决策"],
                "description": "Closing hesitant customers"
            },
            {
                "query": "如何介绍产品",
                "expected_type": ["sales_sop", "champion_case"],
                "expected_content": ["介绍", "话术", "卖点", "价值"],
                "description": "Product introduction techniques"
            }
        ]

        results = []
        total_passed = 0

        for i, test_case in enumerate(test_cases, 1):
            query = test_case["query"]
            expected_types = test_case["expected_type"]
            expected_content = test_case["expected_content"]
            description = test_case["description"]

            logger.info(f"\nTest Case {i}: {description}")
            logger.info(f"Query: '{query}'")

            # Perform search
            start_time = time.time()
            search_results = self.store.search(query, top_k=5, min_score=0.3)
            query_time = (time.time() - start_time) * 1000

            # Check type relevance
            result_types = [r['type'] for r in search_results]
            type_match = any(t in expected_types for t in result_types)

            # Check content relevance
            found_content = []
            for result in search_results:
                text = result['text'].lower()
                for content in expected_content:
                    if content in text:
                        found_content.append(content)

            found_content = list(set(found_content))
            content_relevance = len(found_content) / len(expected_content) if expected_content else 0

            passed = type_match and content_relevance >= 0.3 and len(search_results) > 0
            if passed:
                total_passed += 1

            result = {
                "test_case": i,
                "query": query,
                "description": description,
                "num_results": len(search_results),
                "top_score": search_results[0]['score'] if search_results else 0,
                "query_time_ms": query_time,
                "result_types": result_types,
                "type_match": type_match,
                "found_content": found_content,
                "content_relevance": content_relevance,
                "passed": passed
            }
            results.append(result)

            logger.info(f"  Results: {len(search_results)}")
            logger.info(f"  Top score: {result['top_score']:.4f}")
            logger.info(f"  Query time: {query_time:.2f}ms")
            logger.info(f"  Result types: {result_types[:3]}")
            logger.info(f"  Type match: {'✓' if type_match else '✗'}")
            logger.info(f"  Found content: {found_content}")
            logger.info(f"  Content relevance: {content_relevance*100:.1f}%")
            logger.info(f"  Status: {'PASS' if passed else 'FAIL'}")

            if search_results:
                logger.info(f"  Top result: {search_results[0]['source']}")
                logger.info(f"  Preview: {search_results[0]['text'][:100]}...")

        accuracy = total_passed / len(test_cases) * 100

        summary = {
            "test_name": "Sales Scenario Relevance",
            "total_cases": len(test_cases),
            "passed": total_passed,
            "failed": len(test_cases) - total_passed,
            "accuracy": accuracy,
            "results": results
        }

        logger.info(f"\n[Summary] Sales Scenarios: {total_passed}/{len(test_cases)} passed ({accuracy:.1f}%)")

        return summary

    def test_performance_benchmarks(self) -> Dict[str, Any]:
        """
        Test 3: Performance Benchmarks
        Verify latency and throughput requirements
        """
        logger.info("\n=== Test 3: Performance Benchmarks ===")

        # Test queries
        test_queries = [
            "这个太贵了",
            "我需要再考虑一下",
            "年费问题怎么处理",
            "权益不够用怎么办",
            "和其他卡比有什么优势",
            "客户说要和家人商量",
            "如何介绍产品卖点",
            "处理价格异议的技巧"
        ]

        # Warm-up query
        self.store.search(test_queries[0], top_k=5)

        # Benchmark single queries
        query_times = []
        for query in test_queries:
            start_time = time.time()
            results = self.store.search(query, top_k=5, min_score=0.3)
            query_time = (time.time() - start_time) * 1000
            query_times.append(query_time)

        avg_query_time = sum(query_times) / len(query_times)
        max_query_time = max(query_times)
        min_query_time = min(query_times)

        # Test batch queries
        start_time = time.time()
        batch_results = self.store.batch_search(test_queries, top_k=5, min_score=0.3)
        batch_time = (time.time() - start_time) * 1000
        avg_batch_time = batch_time / len(test_queries)

        # Get system stats
        stats = self.store.get_stats()

        # Performance requirements
        latency_requirement = 50  # ms
        latency_passed = avg_query_time < latency_requirement

        results = {
            "test_name": "Performance Benchmarks",
            "single_query": {
                "avg_time_ms": avg_query_time,
                "min_time_ms": min_query_time,
                "max_time_ms": max_query_time,
                "requirement_ms": latency_requirement,
                "passed": latency_passed
            },
            "batch_query": {
                "total_queries": len(test_queries),
                "total_time_ms": batch_time,
                "avg_time_per_query_ms": avg_batch_time
            },
            "system_stats": {
                "total_documents": stats['total_documents'],
                "embedding_dimension": stats['embedding_dimension'],
                "memory_mb": stats['memory_mb'],
                "cache_hit_rate": stats['cache_hit_rate']
            }
        }

        logger.info(f"\n[Single Query Performance]")
        logger.info(f"  Average: {avg_query_time:.2f}ms")
        logger.info(f"  Min: {min_query_time:.2f}ms")
        logger.info(f"  Max: {max_query_time:.2f}ms")
        logger.info(f"  Requirement: <{latency_requirement}ms")
        logger.info(f"  Status: {'PASS' if latency_passed else 'FAIL'}")

        logger.info(f"\n[Batch Query Performance]")
        logger.info(f"  Total queries: {len(test_queries)}")
        logger.info(f"  Total time: {batch_time:.2f}ms")
        logger.info(f"  Avg per query: {avg_batch_time:.2f}ms")

        logger.info(f"\n[System Statistics]")
        logger.info(f"  Documents: {stats['total_documents']}")
        logger.info(f"  Embedding dim: {stats['embedding_dimension']}")
        logger.info(f"  Memory: {stats['memory_mb']:.2f} MB")
        logger.info(f"  Cache hit rate: {stats['cache_hit_rate']*100:.1f}%")

        return results

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all quality validation tests"""
        logger.info("="*70)
        logger.info("Semantic Search Quality Validation")
        logger.info("="*70)

        start_time = time.time()

        # Run tests
        test1_results = self.test_synonym_understanding()
        test2_results = self.test_sales_scenarios()
        test3_results = self.test_performance_benchmarks()

        total_time = time.time() - start_time

        # Calculate overall accuracy
        total_cases = test1_results['total_cases'] + test2_results['total_cases']
        total_passed = test1_results['passed'] + test2_results['passed']
        overall_accuracy = total_passed / total_cases * 100 if total_cases > 0 else 0

        # Check if meets requirements
        accuracy_requirement = 85  # %
        latency_requirement = 50  # ms

        accuracy_passed = overall_accuracy >= accuracy_requirement
        latency_passed = test3_results['single_query']['passed']

        all_passed = accuracy_passed and latency_passed

        # Summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_test_time_seconds": total_time,
            "test_results": {
                "synonym_understanding": test1_results,
                "sales_scenarios": test2_results,
                "performance_benchmarks": test3_results
            },
            "overall_metrics": {
                "total_test_cases": total_cases,
                "total_passed": total_passed,
                "total_failed": total_cases - total_passed,
                "overall_accuracy": overall_accuracy,
                "accuracy_requirement": accuracy_requirement,
                "accuracy_passed": accuracy_passed,
                "avg_latency_ms": test3_results['single_query']['avg_time_ms'],
                "latency_requirement_ms": latency_requirement,
                "latency_passed": latency_passed,
                "all_requirements_met": all_passed
            }
        }

        # Print final summary
        logger.info("\n" + "="*70)
        logger.info("FINAL SUMMARY")
        logger.info("="*70)
        logger.info(f"\nTest Results:")
        logger.info(f"  Synonym Understanding: {test1_results['passed']}/{test1_results['total_cases']} ({test1_results['accuracy']:.1f}%)")
        logger.info(f"  Sales Scenarios: {test2_results['passed']}/{test2_results['total_cases']} ({test2_results['accuracy']:.1f}%)")
        logger.info(f"  Performance: {'PASS' if latency_passed else 'FAIL'}")

        logger.info(f"\nOverall Metrics:")
        logger.info(f"  Total test cases: {total_cases}")
        logger.info(f"  Passed: {total_passed}")
        logger.info(f"  Failed: {total_cases - total_passed}")
        logger.info(f"  Overall accuracy: {overall_accuracy:.1f}%")
        logger.info(f"  Avg latency: {test3_results['single_query']['avg_time_ms']:.2f}ms")

        logger.info(f"\nRequirements:")
        logger.info(f"  Accuracy >={accuracy_requirement}%: {'✓ PASS' if accuracy_passed else '✗ FAIL'}")
        logger.info(f"  Latency <{latency_requirement}ms: {'✓ PASS' if latency_passed else '✗ FAIL'}")

        logger.info(f"\n{'='*70}")
        if all_passed:
            logger.info("[OK] ALL REQUIREMENTS MET - READY FOR PRODUCTION")
        else:
            logger.info("[WARN] SOME REQUIREMENTS NOT MET - NEEDS IMPROVEMENT")
        logger.info("="*70)

        return summary


def main():
    """Main function"""
    print("="*70)
    print("Semantic Search Quality Validation")
    print("="*70)

    # Initialize vector store
    print("\n[INFO] Initializing vector store...")
    store = SimpleVectorStore()

    # Load data
    data_path = "data/processed/semantic_chunks.json"
    try:
        num_chunks = store.load_data(data_path)
        print(f"[OK] Loaded {num_chunks} chunks")
    except Exception as e:
        print(f"[X] Failed to load data: {e}")
        return False

    # Run validation tests
    validator = SemanticQualityValidator(store)
    results = validator.run_all_tests()

    # Save results
    output_file = Path("data/processed/semantic_quality_report.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Test results saved to: {output_file}")

    # Return success status
    return results['overall_metrics']['all_requirements_met']


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
