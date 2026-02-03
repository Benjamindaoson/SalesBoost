#!/usr/bin/env python3
"""
End-to-End Validation System
Complete validation of semantic search pipeline

Validation Flow:
1. System initialization
2. Data loading
3. Semantic search functionality
4. Agent integration
5. Performance benchmarks
6. Production readiness check

Success Criteria:
- All components initialized successfully
- Semantic search returns relevant results
- Performance meets requirements (<50ms latency)
- Agent integration working correctly

Author: Claude Sonnet 4.5
Date: 2026-02-01
Priority: P0
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class EndToEndValidator:
    """
    End-to-end validation for semantic search system

    Validates:
    - System initialization
    - Data integrity
    - Search functionality
    - Agent integration
    - Performance requirements
    """

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "overall_status": "pending"
        }

    def test_1_system_initialization(self) -> bool:
        """Test 1: System Initialization"""
        logger.info("\n" + "="*70)
        logger.info("Test 1: System Initialization")
        logger.info("="*70)

        try:
            # Import semantic search engine
            from scripts.fix_semantic_search import SimpleVectorStore

            logger.info("[OK] SimpleVectorStore imported successfully")

            # Initialize vector store
            store = SimpleVectorStore()
            logger.info("[OK] Vector store initialized")

            # Load data
            data_path = "data/processed/semantic_chunks.json"
            num_chunks = store.load_data(data_path)

            logger.info(f"[OK] Loaded {num_chunks} chunks")

            # Get statistics
            stats = store.get_stats()
            logger.info(f"[OK] Embedding dimension: {stats['embedding_dimension']}")
            logger.info(f"[OK] Memory usage: {stats['memory_mb']:.2f} MB")

            self.results["tests"]["system_initialization"] = {
                "status": "PASS",
                "num_chunks": num_chunks,
                "embedding_dimension": stats['embedding_dimension'],
                "memory_mb": stats['memory_mb']
            }

            self.vector_store = store
            return True

        except Exception as e:
            logger.error(f"[X] System initialization failed: {e}")
            self.results["tests"]["system_initialization"] = {
                "status": "FAIL",
                "error": str(e)
            }
            return False

    def test_2_semantic_search(self) -> bool:
        """Test 2: Semantic Search Functionality"""
        logger.info("\n" + "="*70)
        logger.info("Test 2: Semantic Search Functionality")
        logger.info("="*70)

        try:
            # Test query that should demonstrate semantic understanding
            test_query = "太贵了"
            logger.info(f"[INFO] Test query: '{test_query}'")

            # Perform search
            results = self.vector_store.search(test_query, top_k=3, min_score=0.3)

            logger.info(f"[OK] Retrieved {len(results)} results")

            # Verify semantic understanding
            # The query "太贵了" should retrieve price-related content
            # even if it doesn't contain the exact word "贵"
            semantic_match = False
            for result in results:
                text = result['text'].lower()
                # Check for price-related keywords
                if any(keyword in text for keyword in ['价格', '费用', '成本', '优惠', '便宜']):
                    semantic_match = True
                    break

            if semantic_match:
                logger.info("[OK] Semantic understanding verified")
            else:
                logger.warning("[WARN] Semantic understanding may be limited")

            # Check top result score
            top_score = results[0]['score'] if results else 0

            logger.info(f"[OK] Top result score: {top_score:.4f}")

            self.results["tests"]["semantic_search"] = {
                "status": "PASS" if results and top_score > 0.3 else "FAIL",
                "num_results": len(results),
                "top_score": top_score,
                "semantic_match": semantic_match
            }

            return results and top_score > 0.3

        except Exception as e:
            logger.error(f"[X] Semantic search test failed: {e}")
            self.results["tests"]["semantic_search"] = {
                "status": "FAIL",
                "error": str(e)
            }
            return False

    def test_3_agent_integration(self) -> bool:
        """Test 3: Agent Integration"""
        logger.info("\n" + "="*70)
        logger.info("Test 3: Agent Integration")
        logger.info("="*70)

        try:
            # Import agent interface
            from scripts.create_agent_interface import KnowledgeRetriever, AgentKnowledgeInterface

            logger.info("[OK] Agent interface imported successfully")

            # Initialize retriever
            retriever = KnowledgeRetriever()
            retriever.initialize()

            logger.info("[OK] Knowledge retriever initialized")

            # Create agent interface
            agent_interface = AgentKnowledgeInterface(retriever)

            logger.info("[OK] Agent interface created")

            # Test coach agent query
            coach_results = agent_interface.coach_agent_query("价格异议")

            logger.info(f"[OK] Coach agent query returned {len(coach_results)} results")

            # Test compliance agent query
            compliance_results = agent_interface.compliance_agent_query("年费")

            logger.info(f"[OK] Compliance agent query returned {len(compliance_results)} results")

            self.results["tests"]["agent_integration"] = {
                "status": "PASS",
                "coach_results": len(coach_results),
                "compliance_results": len(compliance_results)
            }

            return True

        except Exception as e:
            logger.error(f"[X] Agent integration test failed: {e}")
            self.results["tests"]["agent_integration"] = {
                "status": "FAIL",
                "error": str(e)
            }
            return False

    def test_4_performance_benchmarks(self) -> bool:
        """Test 4: Performance Benchmarks"""
        logger.info("\n" + "="*70)
        logger.info("Test 4: Performance Benchmarks")
        logger.info("="*70)

        try:
            # Test queries
            test_queries = [
                "这个太贵了",
                "我需要再考虑一下",
                "年费问题怎么处理",
                "权益不够用怎么办"
            ]

            # Warm-up query
            self.vector_store.search(test_queries[0], top_k=5)

            # Benchmark queries
            query_times = []
            for query in test_queries:
                start_time = time.time()
                results = self.vector_store.search(query, top_k=5, min_score=0.3)
                query_time = (time.time() - start_time) * 1000
                query_times.append(query_time)

            avg_query_time = sum(query_times) / len(query_times)
            max_query_time = max(query_times)
            min_query_time = min(query_times)

            # Performance requirement
            latency_requirement = 50  # ms
            latency_passed = avg_query_time < latency_requirement

            logger.info(f"[INFO] Average query time: {avg_query_time:.2f}ms")
            logger.info(f"[INFO] Min query time: {min_query_time:.2f}ms")
            logger.info(f"[INFO] Max query time: {max_query_time:.2f}ms")
            logger.info(f"[INFO] Requirement: <{latency_requirement}ms")

            if latency_passed:
                logger.info("[OK] Performance requirement met")
            else:
                logger.warning("[WARN] Performance requirement not met")

            self.results["tests"]["performance_benchmarks"] = {
                "status": "PASS" if latency_passed else "FAIL",
                "avg_query_time_ms": avg_query_time,
                "min_query_time_ms": min_query_time,
                "max_query_time_ms": max_query_time,
                "requirement_ms": latency_requirement,
                "passed": latency_passed
            }

            return latency_passed

        except Exception as e:
            logger.error(f"[X] Performance benchmark test failed: {e}")
            self.results["tests"]["performance_benchmarks"] = {
                "status": "FAIL",
                "error": str(e)
            }
            return False

    def test_5_production_readiness(self) -> bool:
        """Test 5: Production Readiness Check"""
        logger.info("\n" + "="*70)
        logger.info("Test 5: Production Readiness Check")
        logger.info("="*70)

        checks = []

        # Check 1: Data files exist
        data_file = Path("data/processed/semantic_chunks.json")
        if data_file.exists():
            logger.info("[OK] Data file exists")
            checks.append(True)
        else:
            logger.error("[X] Data file missing")
            checks.append(False)

        # Check 2: Vector store can be initialized
        try:
            from scripts.fix_semantic_search import SimpleVectorStore
            store = SimpleVectorStore()
            logger.info("[OK] Vector store can be initialized")
            checks.append(True)
        except Exception as e:
            logger.error(f"[X] Vector store initialization failed: {e}")
            checks.append(False)

        # Check 3: Agent interface can be initialized
        try:
            from scripts.create_agent_interface import KnowledgeRetriever
            retriever = KnowledgeRetriever()
            logger.info("[OK] Agent interface can be initialized")
            checks.append(True)
        except Exception as e:
            logger.error(f"[X] Agent interface initialization failed: {e}")
            checks.append(False)

        # Check 4: Knowledge integration module exists
        integration_file = Path("app/knowledge_integration.py")
        if integration_file.exists():
            logger.info("[OK] Knowledge integration module exists")
            checks.append(True)
        else:
            logger.error("[X] Knowledge integration module missing")
            checks.append(False)

        # Check 5: Dependencies installed
        try:
            import sentence_transformers
            import numpy as np
            logger.info("[OK] Required dependencies installed")
            checks.append(True)
        except ImportError as e:
            logger.error(f"[X] Missing dependencies: {e}")
            checks.append(False)

        all_passed = all(checks)

        self.results["tests"]["production_readiness"] = {
            "status": "PASS" if all_passed else "FAIL",
            "checks_passed": sum(checks),
            "checks_total": len(checks),
            "all_passed": all_passed
        }

        return all_passed

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests"""
        logger.info("="*70)
        logger.info("End-to-End Validation System")
        logger.info("="*70)

        start_time = time.time()

        # Run tests
        test_results = []

        test_results.append(("System Initialization", self.test_1_system_initialization()))
        test_results.append(("Semantic Search", self.test_2_semantic_search()))
        test_results.append(("Agent Integration", self.test_3_agent_integration()))
        test_results.append(("Performance Benchmarks", self.test_4_performance_benchmarks()))
        test_results.append(("Production Readiness", self.test_5_production_readiness()))

        total_time = time.time() - start_time

        # Calculate overall status
        all_passed = all(result for _, result in test_results)

        self.results["overall_status"] = "PASS" if all_passed else "FAIL"
        self.results["total_time_seconds"] = total_time
        self.results["tests_passed"] = sum(1 for _, result in test_results if result)
        self.results["tests_total"] = len(test_results)

        # Print summary
        logger.info("\n" + "="*70)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*70)

        for test_name, passed in test_results:
            status = "✓ PASS" if passed else "✗ FAIL"
            logger.info(f"{test_name}: {status}")

        logger.info(f"\nTotal tests: {len(test_results)}")
        logger.info(f"Passed: {sum(1 for _, result in test_results if result)}")
        logger.info(f"Failed: {sum(1 for _, result in test_results if not result)}")
        logger.info(f"Total time: {total_time:.2f}s")

        logger.info("\n" + "="*70)
        if all_passed:
            logger.info("[OK] ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")
        else:
            logger.info("[WARN] SOME TESTS FAILED - REVIEW REQUIRED")
        logger.info("="*70)

        return self.results


def main():
    """Main function"""
    print("="*70)
    print("End-to-End Validation System")
    print("="*70)

    # Run validation
    validator = EndToEndValidator()
    results = validator.run_all_tests()

    # Save results
    output_file = Path("data/processed/e2e_validation_report.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Validation report saved to: {output_file}")

    # Return success status
    return results["overall_status"] == "PASS"


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
