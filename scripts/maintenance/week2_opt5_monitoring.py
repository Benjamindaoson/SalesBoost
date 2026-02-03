#!/usr/bin/env python3
"""
Week 2 优化 5: Prometheus监控和可观测性
实时性能监控 + 分布式追踪 + 用户反馈

性能目标:
- 实时监控所有关键指标
- 分布式追踪定位瓶颈
- 用户反馈收集优化
"""

import time
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


# ============================================================================
# Prometheus 指标定义
# ============================================================================

# 查询计数器
query_counter = Counter(
    'rag_query_total',
    'Total RAG queries',
    ['status', 'intent', 'complexity']
)

# 查询延迟直方图
query_latency = Histogram(
    'rag_query_latency_seconds',
    'RAG query latency in seconds',
    ['stage'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# 缓存命中率
cache_hit_rate = Gauge(
    'rag_cache_hit_rate',
    'Cache hit rate',
    ['cache_type']
)

# LLM token使用
llm_tokens = Counter(
    'rag_llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'type']  # type: prompt, completion
)

# 成本追踪
cost_tracker = Counter(
    'rag_cost_total_cny',
    'Total cost in CNY',
    ['service']  # service: llm, embedding, storage
)

# 错误计数
error_counter = Counter(
    'rag_errors_total',
    'Total errors',
    ['error_type', 'component']
)

# 用户满意度
user_satisfaction = Gauge(
    'rag_user_satisfaction_score',
    'User satisfaction score (0-5)',
    ['feedback_type']
)


# ============================================================================
# 分布式追踪
# ============================================================================

# 初始化OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# 添加控制台导出器 (生产环境应该用Jaeger)
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)


class MonitoredRAGPipeline:
    """带监控的RAG管道"""

    def __init__(self):
        """初始化监控RAG管道"""
        print("[OK] Monitored RAG Pipeline initialized")
        print("  - Prometheus metrics enabled")
        print("  - OpenTelemetry tracing enabled")

    async def process_query(
        self,
        query: str,
        query_vector: List[float],
        retriever,
        reranker,
        llm_client
    ) -> Dict:
        """
        处理查询 (带完整监控)

        Args:
            query: 用户查询
            query_vector: 查询向量
            retriever: 检索器
            reranker: 重排序器
            llm_client: LLM客户端

        Returns:
            查询结果
        """
        start_time = time.time()

        # 创建根span
        with tracer.start_as_current_span("rag_query") as root_span:
            root_span.set_attribute("query", query)
            root_span.set_attribute("query_length", len(query))

            try:
                # Step 1: 检索
                with tracer.start_as_current_span("retrieval") as retrieval_span:
                    retrieval_start = time.time()

                    retrieval_result = retriever.search(
                        query=query,
                        query_vector=query_vector,
                        final_k=20
                    )

                    retrieval_time = time.time() - retrieval_start

                    retrieval_span.set_attribute("result_count", len(retrieval_result.get('results', [])))
                    retrieval_span.set_attribute("latency_ms", retrieval_time * 1000)

                    # 记录延迟
                    query_latency.labels(stage='retrieval').observe(retrieval_time)

                # Step 2: 重排序
                with tracer.start_as_current_span("reranking") as rerank_span:
                    rerank_start = time.time()

                    reranked_results = reranker.rerank(
                        query=query,
                        documents=retrieval_result['results'],
                        top_k=5
                    )

                    rerank_time = time.time() - rerank_start

                    rerank_span.set_attribute("result_count", len(reranked_results))
                    rerank_span.set_attribute("latency_ms", rerank_time * 1000)

                    # 记录延迟
                    query_latency.labels(stage='reranking').observe(rerank_time)

                # Step 3: 生成
                with tracer.start_as_current_span("generation") as gen_span:
                    gen_start = time.time()

                    answer = llm_client.generate(query, reranked_results)

                    gen_time = time.time() - gen_start

                    gen_span.set_attribute("answer_length", len(answer))
                    gen_span.set_attribute("latency_ms", gen_time * 1000)

                    # 记录延迟
                    query_latency.labels(stage='generation').observe(gen_time)

                    # 记录token使用 (模拟)
                    prompt_tokens = 200
                    completion_tokens = 100
                    llm_tokens.labels(model='deepseek-v3', type='prompt').inc(prompt_tokens)
                    llm_tokens.labels(model='deepseek-v3', type='completion').inc(completion_tokens)

                    # 记录成本
                    cost = (prompt_tokens * 0.0014 + completion_tokens * 0.0028) / 1000
                    cost_tracker.labels(service='llm').inc(cost)

                # 总延迟
                total_time = time.time() - start_time
                query_latency.labels(stage='total').observe(total_time)

                # 记录成功
                query_counter.labels(
                    status='success',
                    intent='unknown',
                    complexity='medium'
                ).inc()

                root_span.set_attribute("status", "success")
                root_span.set_attribute("total_latency_ms", total_time * 1000)

                return {
                    "query": query,
                    "answer": answer,
                    "context": reranked_results,
                    "metrics": {
                        "retrieval_time_ms": retrieval_time * 1000,
                        "rerank_time_ms": rerank_time * 1000,
                        "generation_time_ms": gen_time * 1000,
                        "total_time_ms": total_time * 1000
                    }
                }

            except Exception as e:
                # 记录错误
                error_counter.labels(
                    error_type=type(e).__name__,
                    component='rag_pipeline'
                ).inc()

                query_counter.labels(
                    status='error',
                    intent='unknown',
                    complexity='unknown'
                ).inc()

                root_span.set_attribute("status", "error")
                root_span.set_attribute("error", str(e))

                raise


class FeedbackCollector:
    """用户反馈收集器"""

    def __init__(self):
        """初始化反馈收集器"""
        self.feedback_history: List[Dict] = []
        print("[OK] Feedback Collector initialized")

    def collect(
        self,
        query: str,
        answer: str,
        user_action: str,
        rating: Optional[int] = None
    ):
        """
        收集用户反馈

        Args:
            query: 查询文本
            answer: 答案文本
            user_action: 用户动作 (clicked, skipped, thumbs_up, thumbs_down)
            rating: 评分 (1-5)
        """
        feedback = {
            "query": query,
            "answer": answer,
            "action": user_action,
            "rating": rating,
            "timestamp": datetime.now().isoformat()
        }

        self.feedback_history.append(feedback)

        # 更新满意度指标
        if rating:
            user_satisfaction.labels(feedback_type=user_action).set(rating)

        # 低质量告警
        if user_action == "thumbs_down" or (rating and rating <= 2):
            self._alert_low_quality(query, answer, rating)

        print(f"[FEEDBACK] {user_action} - Query: {query[:50]}...")

    def _alert_low_quality(
        self,
        query: str,
        answer: str,
        rating: Optional[int]
    ):
        """低质量告警"""
        print(f"\n[ALERT] Low Quality Response Detected!")
        print(f"  Query: {query}")
        print(f"  Rating: {rating}")
        print(f"  Action: Review and improve")

    def get_stats(self) -> Dict:
        """获取反馈统计"""
        if not self.feedback_history:
            return {}

        total = len(self.feedback_history)
        thumbs_up = sum(1 for f in self.feedback_history if f['action'] == 'thumbs_up')
        thumbs_down = sum(1 for f in self.feedback_history if f['action'] == 'thumbs_down')

        ratings = [f['rating'] for f in self.feedback_history if f['rating']]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        return {
            "total_feedback": total,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "satisfaction_rate": thumbs_up / total if total > 0 else 0,
            "average_rating": avg_rating
        }


def export_metrics() -> str:
    """导出Prometheus指标"""
    return generate_latest(REGISTRY).decode('utf-8')


def test_monitoring_system():
    """测试监控系统"""
    print("\n" + "="*70)
    print("Testing Monitoring and Observability System")
    print("="*70)

    # 初始化监控管道
    pipeline = MonitoredRAGPipeline()
    feedback_collector = FeedbackCollector()

    # 模拟查询
    class MockRetriever:
        def search(self, query, query_vector, final_k):
            time.sleep(0.05)
            return {"results": [{"text": f"Context for {query}"}]}

    class MockReranker:
        def rerank(self, query, documents, top_k):
            time.sleep(0.02)
            return documents[:top_k]

    class MockLLM:
        def generate(self, query, context):
            time.sleep(0.5)
            return f"Answer for: {query}"

    # 测试查询
    test_queries = [
        "信用卡有哪些权益？",
        "百夫长卡的高尔夫权益",
        "如何申请留学生卡？"
    ]

    print("\n[INFO] Processing queries with monitoring...")
    print("="*70)

    import asyncio

    async def process_all():
        for i, query in enumerate(test_queries, 1):
            print(f"\nQuery {i}: {query}")

            query_vector = [0.1] * 1024  # 模拟向量

            result = await pipeline.process_query(
                query=query,
                query_vector=query_vector,
                retriever=MockRetriever(),
                reranker=MockReranker(),
                llm_client=MockLLM()
            )

            print(f"  Total Time: {result['metrics']['total_time_ms']:.1f}ms")

            # 模拟用户反馈
            import random
            actions = ['thumbs_up', 'thumbs_down', 'clicked']
            action = random.choice(actions)
            rating = random.randint(3, 5) if action == 'thumbs_up' else random.randint(1, 3)

            feedback_collector.collect(
                query=query,
                answer=result['answer'],
                user_action=action,
                rating=rating
            )

    asyncio.run(process_all())

    # 显示指标
    print("\n" + "="*70)
    print("Prometheus Metrics")
    print("="*70)

    metrics = export_metrics()
    print(metrics[:1000] + "...")  # 只显示前1000字符

    # 显示反馈统计
    print("\n" + "="*70)
    print("User Feedback Statistics")
    print("="*70)

    feedback_stats = feedback_collector.get_stats()
    print(f"\nTotal Feedback: {feedback_stats['total_feedback']}")
    print(f"Thumbs Up: {feedback_stats['thumbs_up']}")
    print(f"Thumbs Down: {feedback_stats['thumbs_down']}")
    print(f"Satisfaction Rate: {feedback_stats['satisfaction_rate']:.1%}")
    print(f"Average Rating: {feedback_stats['average_rating']:.2f}/5")

    print("\n[SUCCESS] Monitoring system working!")
    print("[INFO] Key features:")
    print("  - Prometheus metrics: Latency, errors, costs")
    print("  - OpenTelemetry tracing: Distributed tracing")
    print("  - User feedback: Real-time satisfaction tracking")
    print("\n[INFO] Next steps:")
    print("  - Deploy Grafana dashboard")
    print("  - Configure Jaeger for tracing")
    print("  - Set up alerting rules")


if __name__ == "__main__":
    test_monitoring_system()
