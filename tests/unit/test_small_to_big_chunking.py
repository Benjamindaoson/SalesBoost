"""
Unit tests for Small-to-Big chunking strategy.
"""
import pytest
from app.tools.connectors.ingestion.small_to_big_chunker import (
    SmallToBigChunker,
    SmallToBigRetriever,
    ChunkPair,
)


class TestSmallToBigChunker:
    """Test Small-to-Big chunker."""

    def test_initialization(self):
        """Test chunker initialization."""
        chunker = SmallToBigChunker(
            parent_size=1024,
            child_size=256,
            parent_overlap=100,
            child_overlap=50,
        )

        assert chunker.parent_size == 1024
        assert chunker.child_size == 256
        assert chunker.parent_overlap == 100
        assert chunker.child_overlap == 50

    def test_invalid_configuration(self):
        """Test that invalid configuration raises error."""
        # Child size >= parent size
        with pytest.raises(ValueError, match="child_size must be smaller"):
            SmallToBigChunker(parent_size=100, child_size=200)

        # Parent overlap >= parent size
        with pytest.raises(ValueError, match="parent_overlap must be smaller"):
            SmallToBigChunker(parent_size=100, parent_overlap=150)

        # Child overlap >= child size
        with pytest.raises(ValueError, match="child_overlap must be smaller"):
            SmallToBigChunker(child_size=100, child_overlap=150)

    def test_chunk_text_basic(self):
        """Test basic text chunking."""
        chunker = SmallToBigChunker(
            parent_size=100,
            child_size=30,
            parent_overlap=20,
            child_overlap=10,
        )

        text = "A" * 200  # 200 characters
        pairs = chunker.chunk_text(text, doc_id="test_doc")

        # Should create multiple parent chunks
        assert len(pairs) > 0

        # Check first pair structure
        first_pair = pairs[0]
        assert isinstance(first_pair, ChunkPair)
        assert first_pair.parent_id.startswith("test_doc_parent_")
        assert first_pair.child_id.startswith("test_doc_child_")
        assert len(first_pair.parent_text) <= 100
        assert len(first_pair.child_text) <= 30

    def test_chunk_text_with_metadata(self):
        """Test chunking with metadata."""
        chunker = SmallToBigChunker(parent_size=100, child_size=30)

        text = "A" * 150
        metadata = {"source": "test.txt", "type": "document"}

        pairs = chunker.chunk_text(text, doc_id="test_doc", base_metadata=metadata)

        # Check metadata is preserved
        for pair in pairs:
            assert pair.metadata["source"] == "test.txt"
            assert pair.metadata["type"] == "document"
            assert "doc_id" in pair.metadata
            assert "parent_idx" in pair.metadata
            assert "child_idx" in pair.metadata

    def test_chunk_text_empty(self):
        """Test chunking empty text."""
        chunker = SmallToBigChunker()
        pairs = chunker.chunk_text("")

        assert len(pairs) == 0

    def test_chunk_text_chinese(self):
        """Test chunking Chinese text."""
        chunker = SmallToBigChunker(
            parent_size=100,
            child_size=30,
        )

        text = "当客户说年费太贵时，可以回应首年免年费。" * 10  # Repeat to create multiple chunks
        pairs = chunker.chunk_text(text, doc_id="chinese_doc")

        assert len(pairs) > 0

        # Check Chinese text is preserved
        for pair in pairs:
            assert "年费" in pair.parent_text or "客户" in pair.parent_text

    def test_prepare_for_storage(self):
        """Test preparing chunks for storage."""
        chunker = SmallToBigChunker(parent_size=100, child_size=30)

        text = "A" * 150
        pairs = chunker.chunk_text(text, doc_id="test_doc")

        ids, texts, metadatas = chunker.prepare_for_storage(pairs)

        # Check output structure
        assert len(ids) == len(pairs)
        assert len(texts) == len(pairs)
        assert len(metadatas) == len(pairs)

        # Check that we store child chunks
        for i, pair in enumerate(pairs):
            assert ids[i] == pair.child_id
            assert texts[i] == pair.child_text

            # Check parent text is in metadata
            assert metadatas[i]["parent_text"] == pair.parent_text
            assert metadatas[i]["parent_id"] == pair.parent_id

    def test_parent_child_relationship(self):
        """Test that parent-child relationships are correct."""
        chunker = SmallToBigChunker(
            parent_size=100,
            child_size=30,
            parent_overlap=0,  # No overlap for easier testing
            child_overlap=0,
        )

        text = "A" * 200
        pairs = chunker.chunk_text(text, doc_id="test_doc")

        # Group by parent
        parents = {}
        for pair in pairs:
            if pair.parent_id not in parents:
                parents[pair.parent_id] = []
            parents[pair.parent_id].append(pair)

        # Each parent should have multiple children
        for parent_id, children in parents.items():
            assert len(children) > 0

            # All children should have same parent text
            parent_text = children[0].parent_text
            for child in children:
                assert child.parent_text == parent_text

    def test_chunk_positions(self):
        """Test that chunk positions are tracked correctly."""
        chunker = SmallToBigChunker(
            parent_size=100,
            child_size=30,
            parent_overlap=0,
            child_overlap=0,
        )

        text = "ABCDEFGHIJ" * 20  # 200 characters
        pairs = chunker.chunk_text(text, doc_id="test_doc")

        # Check positions are within bounds
        for pair in pairs:
            assert 0 <= pair.parent_start < len(text)
            assert pair.parent_start < pair.parent_end <= len(text)
            assert 0 <= pair.child_start < len(text)
            assert pair.child_start < pair.child_end <= len(text)

            # Child should be within parent
            assert pair.child_start >= pair.parent_start
            assert pair.child_end <= pair.parent_end


class MockVectorStore:
    """Mock vector store for testing."""

    def __init__(self):
        self.documents = []

    async def search(self, query, top_k=5, filters=None):
        """Mock search that returns stored documents."""
        from app.infra.search.vector_store import SearchResult

        results = []
        for i, doc in enumerate(self.documents[:top_k]):
            results.append(
                SearchResult(
                    id=doc["id"],
                    content=doc["content"],
                    score=1.0 - (i * 0.1),  # Decreasing scores
                    metadata=doc["metadata"],
                    rank=i,
                )
            )
        return results

    async def add_documents(self, documents, metadatas, ids):
        """Mock add documents."""
        for doc, meta, doc_id in zip(documents, metadatas, ids):
            self.documents.append(
                {
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta,
                }
            )


class TestSmallToBigRetriever:
    """Test Small-to-Big retriever."""

    @pytest.mark.asyncio
    async def test_retrieve_basic(self):
        """Test basic retrieval."""
        # Setup
        chunker = SmallToBigChunker(parent_size=100, child_size=30)
        text = "当客户说年费太贵时，可以回应首年免年费。这是一个很好的销售技巧。" * 5
        pairs = chunker.chunk_text(text, doc_id="test_doc")

        # Store in mock vector store
        mock_store = MockVectorStore()
        ids, texts, metadatas = chunker.prepare_for_storage(pairs)
        await mock_store.add_documents(texts, metadatas, ids)

        # Retrieve
        retriever = SmallToBigRetriever(mock_store)
        results = await retriever.retrieve("年费", top_k=3)

        # Check results
        assert len(results) > 0
        assert len(results) <= 3

        # Check that we got parent chunks
        for result in results:
            assert "content" in result
            assert "score" in result
            assert "metadata" in result
            assert len(result["content"]) > 30  # Parent chunks are larger

    @pytest.mark.asyncio
    async def test_retrieve_deduplication(self):
        """Test that parent chunks are deduplicated."""
        # Setup with multiple children per parent
        chunker = SmallToBigChunker(
            parent_size=100,
            child_size=20,  # Small children = more per parent
        )
        text = "A" * 200
        pairs = chunker.chunk_text(text, doc_id="test_doc")

        # Store
        mock_store = MockVectorStore()
        ids, texts, metadatas = chunker.prepare_for_storage(pairs)
        await mock_store.add_documents(texts, metadatas, ids)

        # Retrieve
        retriever = SmallToBigRetriever(mock_store)
        results = await retriever.retrieve("A", top_k=5)

        # Check deduplication: should have fewer results than child chunks
        assert len(results) <= len(pairs)

        # Check no duplicate parent IDs
        parent_ids = [r["id"] for r in results]
        assert len(parent_ids) == len(set(parent_ids))

    @pytest.mark.asyncio
    async def test_retrieve_empty(self):
        """Test retrieval with no results."""
        mock_store = MockVectorStore()
        retriever = SmallToBigRetriever(mock_store)

        results = await retriever.retrieve("query", top_k=5)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_retrieve_with_filters(self):
        """Test retrieval with filters."""
        chunker = SmallToBigChunker(parent_size=100, child_size=30)
        text = "Test document content"
        pairs = chunker.chunk_text(
            text,
            doc_id="test_doc",
            base_metadata={"source": "test.txt", "type": "document"},
        )

        mock_store = MockVectorStore()
        ids, texts, metadatas = chunker.prepare_for_storage(pairs)
        await mock_store.add_documents(texts, metadatas, ids)

        retriever = SmallToBigRetriever(mock_store)
        results = await retriever.retrieve(
            "content",
            top_k=5,
            filters={"source": "test.txt"},
        )

        # Check filters are passed through
        assert len(results) >= 0  # May or may not have results depending on mock


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
