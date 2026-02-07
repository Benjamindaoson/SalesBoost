"""
完整的 RAG 3.0 集成测试套件

测试覆盖：
1. 智能路由系统
2. 父子分块
3. BGE-M3 双路检索
4. HyDE 检索
5. Self-RAG
6. RAGAS 评估
"""
import pytest


class TestSmartRouting:
    """测试智能路由系统"""

    @pytest.mark.asyncio
    async def test_pdf_routing_simple(self):
        """测试简单 PDF 路由到快速处理器"""
        from app.tools.connectors.ingestion.smart_router import SmartIngestionRouter

        router = SmartIngestionRouter()

        # 创建简单 PDF（纯文本）
        simple_pdf = b"%PDF-1.4\n" + b"Simple text content" * 100

        decision = router.route(simple_pdf, "simple.pdf")

        assert decision.complexity.value == "low"
        assert decision.processor == "pymupdf"
        assert decision.estimated_cost < 0.01

    @pytest.mark.asyncio
    async def test_pdf_routing_complex(self):
        """测试复杂 PDF 路由到高级处理器"""
        from app.tools.connectors.ingestion.smart_router import SmartIngestionRouter

        router = SmartIngestionRouter()

        # 创建大文件（模拟扫描件）
        large_pdf = b"%PDF-1.4\n" + b"x" * (10 * 1024 * 1024)  # 10MB

        decision = router.route(large_pdf, "scanned.pdf")

        assert decision.complexity.value == "high"
        assert decision.estimated_cost > 0.05

    @pytest.mark.asyncio
    async def test_image_routing(self):
        """测试图片路由"""
        from app.tools.connectors.ingestion.smart_router import SmartIngestionRouter

        router = SmartIngestionRouter()

        # 小图片
        small_image = b"\x89PNG\r\n" + b"x" * 1000

        decision = router.route(small_image, "icon.png")

        assert decision.data_type.value == "image"
        assert decision.complexity.value in ["low", "medium"]

    @pytest.mark.asyncio
    async def test_cost_optimization(self):
        """测试成本优化效果"""
        from app.tools.connectors.ingestion.smart_router import SmartIngestionRouter

        router = SmartIngestionRouter()

        # 模拟 1000 份文档
        decisions = []

        # 70% 简单文档
        for i in range(700):
            simple_pdf = b"%PDF-1.4\n" + b"text" * 100
            decision = router.route(simple_pdf, f"simple_{i}.pdf")
            decisions.append(decision)

        # 30% 复杂文档
        for i in range(300):
            complex_pdf = b"%PDF-1.4\n" + b"x" * (6 * 1024 * 1024)
            decision = router.route(complex_pdf, f"complex_{i}.pdf")
            decisions.append(decision)

        # 计算统计
        stats = router.get_statistics(decisions)

        # 验证成本优化
        avg_cost = stats["avg_cost_per_doc"]
        assert avg_cost < 0.05  # 平均成本应该很低


class TestSmallToBigChunking:
    """测试父子分块"""

    def test_chunking_basic(self):
        """测试基础分块"""
        from app.tools.connectors.ingestion.small_to_big_chunker import SmallToBigChunker

        chunker = SmallToBigChunker(
            parent_size=100,
            child_size=30,
        )

        text = "A" * 200
        pairs = chunker.chunk_text(text, doc_id="test")

        assert len(pairs) > 0
        assert all(len(p.parent_text) <= 100 for p in pairs)
        assert all(len(p.child_text) <= 30 for p in pairs)

    def test_parent_child_relationship(self):
        """测试父子关系"""
        from app.tools.connectors.ingestion.small_to_big_chunker import SmallToBigChunker

        chunker = SmallToBigChunker(
            parent_size=100,
            child_size=30,
        )

        text = "当客户说年费太贵时，可以回应首年免年费。" * 10
        pairs = chunker.chunk_text(text, doc_id="test")

        # 验证子块在父块内
        for pair in pairs:
            assert pair.child_start >= pair.parent_start
            assert pair.child_end <= pair.parent_end

    @pytest.mark.asyncio
    async def test_retrieval_with_small_to_big(self):
        """测试使用父子分块的检索"""
        from app.tools.connectors.ingestion.small_to_big_chunker import (
            SmallToBigChunker,
            SmallToBigRetriever,
        )

        # 创建 mock vector store
        class MockVectorStore:
            def __init__(self):
                self.documents = []

            async def search(self, query, top_k=5, filters=None):
                from app.infra.search.vector_store import SearchResult

                return [
                    SearchResult(
                        id=doc["id"],
                        content=doc["content"],
                        score=1.0,
                        metadata=doc["metadata"],
                        rank=i,
                    )
                    for i, doc in enumerate(self.documents[:top_k])
                ]

            async def add_documents(self, documents, metadatas, ids):
                for doc, meta, doc_id in zip(documents, metadatas, ids):
                    self.documents.append(
                        {"id": doc_id, "content": doc, "metadata": meta}
                    )

        # 准备数据
        chunker = SmallToBigChunker(parent_size=100, child_size=30)
        text = "当客户说年费太贵时，可以回应首年免年费。" * 10
        pairs = chunker.chunk_text(text, doc_id="test")

        # 存储
        mock_store = MockVectorStore()
        ids, texts, metadatas = chunker.prepare_for_storage(pairs)
        await mock_store.add_documents(texts, metadatas, ids)

        # 检索
        retriever = SmallToBigRetriever(mock_store)
        results = await retriever.retrieve("年费", top_k=3)

        assert len(results) > 0
        assert all("parent_text" in r["metadata"] for r in results)


class TestBGEM3Retrieval:
    """测试 BGE-M3 双路检索"""

    @pytest.mark.asyncio
    async def test_bgem3_encoding(self):
        """测试 BGE-M3 编码"""
        from app.infra.search.bgem3_retriever import BGEM3Encoder

        encoder = BGEM3Encoder.get_instance()

        texts = ["当客户说年费太贵时", "首年免年费优惠"]
        embeddings = encoder.encode(texts, return_dense=True, return_sparse=True)

        assert len(embeddings) == 2
        assert all(len(e.dense_vector) == 1024 for e in embeddings)
        assert all(isinstance(e.sparse_vector, dict) for e in embeddings)

    @pytest.mark.asyncio
    async def test_dual_path_retrieval(self):
        """测试双路检索"""
        from app.infra.search.bgem3_retriever import (
            BGEM3Encoder,
            BGEM3DualPathRetriever,
        )

        encoder = BGEM3Encoder.get_instance()
        retriever = BGEM3DualPathRetriever(encoder, fusion_method="rrf")

        # 准备文档
        texts = [
            "当客户说年费太贵时，可以回应首年免年费",
            "首年免年费优惠政策说明",
            "年费收费标准和优惠活动",
        ]

        embeddings = encoder.encode(texts, return_dense=True, return_sparse=True)

        documents = [
            {
                "id": f"doc{i}",
                "content": text,
                "dense_vector": emb.dense_vector,
                "sparse_vector": emb.sparse_vector,
            }
            for i, (text, emb) in enumerate(zip(texts, embeddings))
        ]

        # 检索
        results = await retriever.retrieve(
            query="年费太贵怎么办", documents=documents, top_k=2
        )

        assert len(results) == 2
        assert all("score" in r for r in results)


class TestHyDE:
    """测试 HyDE"""

    @pytest.mark.asyncio
    async def test_hypothetical_document_generation(self):
        """测试假设文档生成"""
        from app.retrieval.hyde_retriever import HyDEGenerator
        import openai

        # 需要 OpenAI API key
        if not openai.api_key:
            pytest.skip("OpenAI API key not configured")

        generator = HyDEGenerator(
            llm_client=openai.AsyncOpenAI(), model="gpt-4o-mini"
        )

        hyp_doc = await generator.generate_hypothetical_document(
            query="客户说年费太贵怎么办？", domain="sales", language="zh"
        )

        assert len(hyp_doc) > 0
        assert "年费" in hyp_doc or "免费" in hyp_doc


class TestSelfRAG:
    """测试 Self-RAG"""

    @pytest.mark.asyncio
    async def test_reflection(self):
        """测试反思功能"""
        from app.retrieval.self_rag import ReflectionAgent
        import openai

        if not openai.api_key:
            pytest.skip("OpenAI API key not configured")

        agent = ReflectionAgent(llm_client=openai.AsyncOpenAI())

        reflection = await agent.reflect(
            query="年费太贵怎么办？",
            answer="可以免年费",
            contexts=["首年免年费优惠政策"],
        )

        assert reflection.relevance_score >= 0.0
        assert reflection.faithfulness_score >= 0.0
        assert reflection.completeness_score >= 0.0


class TestRAGAS:
    """测试 RAGAS 评估"""

    @pytest.mark.asyncio
    async def test_ragas_evaluation(self):
        """测试 RAGAS 评估"""
        from app.evaluation.ragas_evaluator import (
            RAGASEvaluator,
            RAGASEvaluationInput,
        )
        import openai

        if not openai.api_key:
            pytest.skip("OpenAI API key not configured")

        evaluator = RAGASEvaluator(llm_client=openai.AsyncOpenAI())

        input_data = RAGASEvaluationInput(
            question="客户说年费太贵怎么办？",
            answer="可以告诉客户首年免年费，第二年开始收取年费。",
            contexts=["首年免年费优惠政策说明", "年费收费标准"],
            ground_truth="首年免年费，第二年开始收取。",
        )

        metrics = await evaluator.evaluate(input_data)

        assert 0.0 <= metrics.context_precision <= 1.0
        assert 0.0 <= metrics.faithfulness <= 1.0
        assert 0.0 <= metrics.overall_score <= 1.0


class TestEndToEnd:
    """端到端集成测试"""

    @pytest.mark.asyncio
    async def test_complete_rag_pipeline(self):
        """测试完整 RAG 流程"""
        from app.tools.connectors.ingestion.streaming_pipeline import (
            StreamingIngestionPipeline,
        )
        from app.infra.search.vector_store import VectorStoreAdapter

        # 初始化
        vector_store = VectorStoreAdapter(collection_name="test_collection")

        pipeline = StreamingIngestionPipeline(
            vector_store=vector_store,
            use_small_to_big=True,
            use_smart_routing=True,
        )

        # 摄入文档
        text = "当客户说年费太贵时，可以回应首年免年费。" * 10
        result = await pipeline.ingest_bytes(
            source_id="test_001",
            filename="test.txt",
            data=text.encode("utf-8"),
            base_metadata={"type": "script"},
        )

        assert result["status"] == "indexed"
        assert result["chunks_count"] > 0

        # 检索
        search_results = await vector_store.search("年费", top_k=3)

        assert len(search_results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
