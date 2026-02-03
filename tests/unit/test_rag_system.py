"""
Unit tests for RAG system components.

Tests BM25 retriever, embedding manager, vector store, and GraphRAG.
"""
import pytest
import asyncio
from typing import List, Dict, Any

# BM25 Retriever Tests
from app.infra.search.bm25_retriever import BM25Retriever, AsyncBM25Adapter


class TestBM25Retriever:
    """Test BM25 retriever functionality."""

    @pytest.fixture
    def sample_documents(self) -> List[Dict[str, Any]]:
        """Sample documents for testing."""
        return [
            {
                "id": "doc1",
                "content": "当客户说年费太贵时，可以回应首年免年费",
                "metadata": {"stage": "objection", "type": "script"}
            },
            {
                "id": "doc2",
                "content": "信用卡产品具有积分兑换功能",
                "metadata": {"stage": "presentation", "type": "feature"}
            },
            {
                "id": "doc3",
                "content": "促单成交阶段需要强调产品优势",
                "metadata": {"stage": "closing", "type": "technique"}
            },
        ]

    def test_bm25_initialization(self, sample_documents):
        """Test BM25 retriever initialization."""
        retriever = BM25Retriever(documents=sample_documents)

        assert retriever is not None
        assert retriever.get_document_count() == 3

    def test_bm25_tokenization(self):
        """Test Chinese tokenization."""
        retriever = BM25Retriever(use_jieba=True)

        tokens = retriever._tokenize("年费太贵")
        assert len(tokens) > 0
        assert all(isinstance(t, str) for t in tokens)

    @pytest.mark.asyncio
    async def test_bm25_search(self, sample_documents):
        """Test BM25 search."""
        retriever = BM25Retriever(documents=sample_documents)

        results = await retriever.search("年费", top_k=2)

        assert len(results) > 0
        assert results[0].id == "doc1"
        assert results[0].score > 0

    @pytest.mark.asyncio
    async def test_bm25_search_with_filters(self, sample_documents):
        """Test BM25 search with metadata filters."""
        retriever = BM25Retriever(documents=sample_documents)

        results = await retriever.search(
            "产品",
            top_k=5,
            filters={"stage": "presentation"}
        )

        assert len(results) > 0
        assert all(r.metadata.get("stage") == "presentation" for r in results)

    @pytest.mark.asyncio
    async def test_bm25_empty_query(self, sample_documents):
        """Test BM25 with empty query."""
        retriever = BM25Retriever(documents=sample_documents)

        results = await retriever.search("", top_k=5)

        assert len(results) == 0

    def test_bm25_add_documents(self, sample_documents):
        """Test adding documents to BM25 index."""
        retriever = BM25Retriever()

        assert retriever.get_document_count() == 0

        retriever.add_documents(sample_documents)

        assert retriever.get_document_count() == 3

    def test_bm25_clear(self, sample_documents):
        """Test clearing BM25 index."""
        retriever = BM25Retriever(documents=sample_documents)

        assert retriever.get_document_count() == 3

        retriever.clear()

        assert retriever.get_document_count() == 0


# Embedding Manager Tests
from app.infra.search.embedding_manager import (
    EmbeddingModelManager,
    EMBEDDING_MODELS,
    get_embedding_manager
)


class TestEmbeddingManager:
    """Test embedding model manager."""

    def test_list_models(self):
        """Test listing supported models."""
        models = EmbeddingModelManager.list_models()

        assert len(models) > 0
        assert "paraphrase-multilingual-MiniLM-L12-v2" in models
        assert "shibing624/text2vec-base-chinese" in models

    def test_get_model_info(self):
        """Test getting model information."""
        info = EmbeddingModelManager.get_model_info("paraphrase-multilingual-MiniLM-L12-v2")

        assert info is not None
        assert info.dimension == 384
        assert info.multilingual is True

    def test_embedding_manager_initialization(self):
        """Test embedding manager initialization."""
        manager = EmbeddingModelManager(
            model_name="paraphrase-multilingual-MiniLM-L12-v2",
            device="cpu"
        )

        assert manager is not None
        assert manager.model_name == "paraphrase-multilingual-MiniLM-L12-v2"

    def test_get_dimension(self):
        """Test getting embedding dimension."""
        manager = get_embedding_manager(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )

        dimension = manager.get_dimension()

        assert dimension == 384

    def test_encode_single(self):
        """Test encoding single text."""
        manager = get_embedding_manager(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )

        embedding = manager.encode_single("测试文本")

        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    def test_encode_batch(self):
        """Test encoding batch of texts."""
        manager = get_embedding_manager(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )

        texts = ["文本1", "文本2", "文本3"]
        embeddings = manager.encode(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)

    @pytest.mark.asyncio
    async def test_encode_async(self):
        """Test async encoding."""
        manager = get_embedding_manager(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )

        texts = ["异步文本1", "异步文本2"]
        embeddings = await manager.encode_async(texts)

        assert len(embeddings) == 2
        assert all(len(emb) == 384 for emb in embeddings)


# Vector Store Tests
from app.infra.search.vector_store import (
    VectorStoreAdapter,
    HybridSearchEngine,
    BGEReranker,
    SearchResult
)


class TestVectorStore:
    """Test vector store functionality."""

    @pytest.mark.asyncio
    async def test_vector_store_initialization(self):
        """Test vector store initialization with auto dimension detection."""
        store = VectorStoreAdapter(
            collection_name="test_collection",
            embedding_model="paraphrase-multilingual-MiniLM-L12-v2"
        )

        assert store is not None
        assert store.vector_size == 384  # Auto-detected

    @pytest.mark.asyncio
    async def test_add_documents(self):
        """Test adding documents to vector store."""
        store = VectorStoreAdapter(
            collection_name="test_add_docs",
            embedding_model="paraphrase-multilingual-MiniLM-L12-v2"
        )

        documents = ["文档1", "文档2", "文档3"]
        metadatas = [{"type": "test"} for _ in documents]

        ids = await store.add_documents(documents, metadatas)

        assert len(ids) == 3
        assert all(isinstance(id, str) for id in ids)


class TestHybridSearch:
    """Test hybrid search functionality."""

    def test_rrf_fusion(self):
        """Test RRF fusion algorithm."""
        vec_results = [
            SearchResult(id="doc1", content="content1", score=0.9, rank=0),
            SearchResult(id="doc2", content="content2", score=0.8, rank=1),
        ]

        kw_results = [
            SearchResult(id="doc2", content="content2", score=10.0, rank=0),
            SearchResult(id="doc3", content="content3", score=8.0, rank=1),
        ]

        # Create mock stores
        class MockStore:
            async def search(self, query, top_k):
                return []

        engine = HybridSearchEngine(MockStore(), MockStore(), rrf_k=60)
        fused = engine.rrf_fusion(vec_results, kw_results, limit=3)

        assert len(fused) <= 3
        # doc2 should rank higher (appears in both)
        assert fused[0].id == "doc2"


class TestBGEReranker:
    """Test BGE reranker."""

    def test_reranker_initialization(self):
        """Test reranker initialization."""
        reranker = BGEReranker.get_instance()

        assert reranker is not None

    def test_rerank(self):
        """Test reranking results."""
        reranker = BGEReranker.get_instance()

        results = [
            SearchResult(id="doc1", content="年费太贵", score=0.5, rank=0),
            SearchResult(id="doc2", content="首年免年费", score=0.6, rank=1),
            SearchResult(id="doc3", content="无关内容", score=0.7, rank=2),
        ]

        reranked = reranker.rerank("年费", results, top_k=2)

        assert len(reranked) == 2
        # Reranked scores should be different
        assert reranked[0].score != results[0].score


# GraphRAG Tests
from app.infra.search.graph_rag import (
    GraphRAGService,
    KnowledgeGraph,
    Entity,
    Relation,
    EntityType,
    RelationType,
)


class TestGraphRAG:
    """Test GraphRAG functionality."""

    def test_knowledge_graph_initialization(self):
        """Test knowledge graph initialization."""
        graph = KnowledgeGraph()

        assert graph is not None
        assert len(graph.entities) == 0
        assert len(graph.relations) == 0

    def test_add_entity(self):
        """Test adding entity to graph."""
        graph = KnowledgeGraph()

        entity = Entity(
            id="test_entity",
            name="测试实体",
            type=EntityType.PRODUCT
        )

        graph.add_entity(entity)

        assert len(graph.entities) == 1
        assert graph.get_entity("test_entity") == entity

    def test_add_relation(self):
        """Test adding relation to graph."""
        graph = KnowledgeGraph()

        # Add entities first
        entity1 = Entity(id="e1", name="产品", type=EntityType.PRODUCT)
        entity2 = Entity(id="e2", name="功能", type=EntityType.FEATURE)

        graph.add_entity(entity1)
        graph.add_entity(entity2)

        # Add relation
        relation = Relation(
            id="rel1",
            source_id="e1",
            target_id="e2",
            type=RelationType.HAS_FEATURE
        )

        graph.add_relation(relation)

        assert len(graph.relations) == 1

    def test_get_neighbors(self):
        """Test getting neighboring entities."""
        graph = KnowledgeGraph()

        # Create simple graph: e1 -> e2 -> e3
        e1 = Entity(id="e1", name="E1", type=EntityType.PRODUCT)
        e2 = Entity(id="e2", name="E2", type=EntityType.FEATURE)
        e3 = Entity(id="e3", name="E3", type=EntityType.BENEFIT)

        graph.add_entity(e1)
        graph.add_entity(e2)
        graph.add_entity(e3)

        r1 = Relation(id="r1", source_id="e1", target_id="e2", type=RelationType.HAS_FEATURE)
        r2 = Relation(id="r2", source_id="e2", target_id="e3", type=RelationType.PROVIDES_BENEFIT)

        graph.add_relation(r1)
        graph.add_relation(r2)

        # Get 1-hop neighbors of e1
        neighbors = graph.get_neighbors("e1", max_hops=1)

        assert "e2" in neighbors

        # Get 2-hop neighbors of e1
        neighbors = graph.get_neighbors("e1", max_hops=2)

        assert "e2" in neighbors
        assert "e3" in neighbors

    def test_extract_subgraph(self):
        """Test extracting subgraph."""
        graph = KnowledgeGraph()

        # Create graph
        e1 = Entity(id="e1", name="E1", type=EntityType.PRODUCT)
        e2 = Entity(id="e2", name="E2", type=EntityType.FEATURE)

        graph.add_entity(e1)
        graph.add_entity(e2)

        r1 = Relation(id="r1", source_id="e1", target_id="e2", type=RelationType.HAS_FEATURE)
        graph.add_relation(r1)

        # Extract subgraph
        subgraph = graph.extract_subgraph(seed_entities=["e1"], max_hops=1)

        assert len(subgraph.entities) == 2
        assert len(subgraph.relations) == 1
        assert len(subgraph.triples) == 1

    @pytest.mark.asyncio
    async def test_graphrag_service_initialization(self):
        """Test GraphRAG service initialization."""
        service = GraphRAGService(org_id="test_org")

        assert service is not None
        assert service.knowledge_graph is not None
        assert service.entity_extractor is not None
        assert service.relation_extractor is not None

    @pytest.mark.asyncio
    async def test_document_ingestion(self):
        """Test document ingestion."""
        service = GraphRAGService(org_id="test_org")

        result = await service.ingest_document(
            doc_id="test_doc",
            text="当客户说年费太贵时，可以回应首年免年费"
        )

        assert result is not None
        assert "total_entities" in result
        assert "total_relations" in result

    @pytest.mark.asyncio
    async def test_graphrag_search(self):
        """Test GraphRAG search."""
        service = GraphRAGService(org_id="test_org")

        # Ingest some data first
        await service.ingest_document(
            doc_id="doc1",
            text="当客户说年费太贵时，可以回应首年免年费"
        )

        # Search
        result = await service.search(query="年费", mode="local", top_k=5)

        assert result is not None
        assert result.mode == "local"
        assert result.context is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
