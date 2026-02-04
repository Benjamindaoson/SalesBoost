"""
Unit tests for BGE-Reranker integration.

Tests cover:
- BGE reranker initialization
- Reranking functionality
- Singleton pattern
- Error handling
- Performance benchmarks
"""
import pytest
from unittest.mock import patch, MagicMock
from app.infra.search.vector_store import BGEReranker, SearchResult


class TestBGERerankerInitialization:
    """Test BGE reranker initialization and model loading."""

    def test_init_with_default_model(self):
        """Test initialization with default model name."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            reranker = BGEReranker()
            assert reranker.model_name == "BAAI/bge-reranker-base"
            assert reranker.batch_size == 32

    def test_init_with_custom_model(self):
        """Test initialization with custom model name."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            reranker = BGEReranker(model_name="BAAI/bge-reranker-large", batch_size=16)
            assert reranker.model_name == "BAAI/bge-reranker-large"
            assert reranker.batch_size == 16

    def test_singleton_pattern(self):
        """Test that BGEReranker follows singleton pattern."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            # Reset singleton
            BGEReranker._instance = None
            BGEReranker._model = None

            instance1 = BGEReranker.get_instance()
            instance2 = BGEReranker.get_instance()

            assert instance1 is instance2

    def test_model_loading_failure(self):
        """Test graceful handling of model loading failure."""
        with patch('app.infra.search.vector_store.FlagReranker', side_effect=Exception("Model not found")):
            BGEReranker()
            assert BGEReranker._model is None

    def test_flag_embedding_not_available(self):
        """Test behavior when FlagEmbedding is not installed."""
        with patch('app.infra.search.vector_store.FlagReranker', None):
            reranker = BGEReranker()
            results = reranker.rerank("test query", [])
            assert results == []


class TestBGERerankerFunctionality:
    """Test BGE reranker core functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.sample_results = [
            SearchResult(id="1", content="Python is a programming language", score=0.8, metadata={}),
            SearchResult(id="2", content="Java is also a programming language", score=0.7, metadata={}),
            SearchResult(id="3", content="Machine learning uses Python", score=0.6, metadata={}),
            SearchResult(id="4", content="Web development with JavaScript", score=0.5, metadata={}),
        ]

    def test_rerank_empty_results(self):
        """Test reranking with empty results list."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            reranker = BGEReranker()
            results = reranker.rerank("test query", [])
            assert results == []

    def test_rerank_single_result(self):
        """Test reranking with single result."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            mock_model = MagicMock()
            mock_model.compute_score.return_value = 0.95
            BGEReranker._model = mock_model

            reranker = BGEReranker()
            results = reranker.rerank("Python programming", [self.sample_results[0]])

            assert len(results) == 1
            assert results[0].id == "1"
            assert results[0].score == 0.95

    def test_rerank_multiple_results(self):
        """Test reranking with multiple results."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            mock_model = MagicMock()
            # Simulate BGE scores (higher is better)
            mock_model.compute_score.return_value = [0.9, 0.5, 0.95, 0.3]
            BGEReranker._model = mock_model

            reranker = BGEReranker()
            results = reranker.rerank("Python programming", self.sample_results)

            # Should be sorted by BGE score descending
            assert len(results) == 4
            assert results[0].id == "3"  # Highest score (0.95)
            assert results[1].id == "1"  # Second highest (0.9)
            assert results[2].id == "2"  # Third (0.5)
            assert results[3].id == "4"  # Lowest (0.3)

    def test_rerank_with_top_k(self):
        """Test reranking with top_k parameter."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            mock_model = MagicMock()
            mock_model.compute_score.return_value = [0.9, 0.5, 0.95, 0.3]
            BGEReranker._model = mock_model

            reranker = BGEReranker()
            results = reranker.rerank("Python programming", self.sample_results, top_k=2)

            assert len(results) == 2
            assert results[0].id == "3"
            assert results[1].id == "1"

    def test_rerank_assigns_ranks(self):
        """Test that reranking assigns correct ranks."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            mock_model = MagicMock()
            mock_model.compute_score.return_value = [0.9, 0.5, 0.95, 0.3]
            BGEReranker._model = mock_model

            reranker = BGEReranker()
            results = reranker.rerank("Python programming", self.sample_results)

            assert results[0].rank == 0
            assert results[1].rank == 1
            assert results[2].rank == 2
            assert results[3].rank == 3

    def test_rerank_preserves_metadata(self):
        """Test that reranking preserves result metadata."""
        results_with_metadata = [
            SearchResult(id="1", content="Test content", score=0.8, metadata={"source": "doc1"}),
            SearchResult(id="2", content="Another content", score=0.7, metadata={"source": "doc2"}),
        ]

        with patch('app.infra.search.vector_store.FlagReranker'):
            mock_model = MagicMock()
            mock_model.compute_score.return_value = [0.6, 0.9]
            BGEReranker._model = mock_model

            reranker = BGEReranker()
            results = reranker.rerank("test query", results_with_metadata)

            assert results[0].metadata == {"source": "doc2"}
            assert results[1].metadata == {"source": "doc1"}

    def test_rerank_error_handling(self):
        """Test error handling during reranking."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            mock_model = MagicMock()
            mock_model.compute_score.side_effect = Exception("Reranking failed")
            BGEReranker._model = mock_model

            reranker = BGEReranker()
            results = reranker.rerank("test query", self.sample_results)

            # Should return original results on error
            assert results == self.sample_results

    def test_rerank_model_not_loaded(self):
        """Test reranking when model is not loaded."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            BGEReranker._model = None

            reranker = BGEReranker()
            results = reranker.rerank("test query", self.sample_results)

            # Should return original results
            assert results == self.sample_results


class TestBGERerankerPerformance:
    """Test BGE reranker performance characteristics."""

    def test_batch_processing(self):
        """Test that batch_size parameter is used correctly."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            mock_model = MagicMock()
            mock_model.compute_score.return_value = [0.5] * 10
            BGEReranker._model = mock_model

            reranker = BGEReranker(batch_size=5)
            results = [
                SearchResult(id=str(i), content=f"Content {i}", score=0.5, metadata={})
                for i in range(10)
            ]

            reranker.rerank("test query", results)

            # Verify compute_score was called with batch_size parameter
            mock_model.compute_score.assert_called_once()
            call_args = mock_model.compute_score.call_args
            assert call_args[1]['batch_size'] == 5

    def test_large_result_set(self):
        """Test reranking with large result set."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            mock_model = MagicMock()
            # Generate scores for 100 results
            mock_model.compute_score.return_value = [0.5 + (i * 0.001) for i in range(100)]
            BGEReranker._model = mock_model

            reranker = BGEReranker()
            results = [
                SearchResult(id=str(i), content=f"Content {i}", score=0.5, metadata={})
                for i in range(100)
            ]

            reranked = reranker.rerank("test query", results, top_k=10)

            assert len(reranked) == 10
            # Verify results are sorted correctly
            for i in range(len(reranked) - 1):
                assert reranked[i].score >= reranked[i + 1].score


class TestBGERerankerIntegration:
    """Integration tests for BGE reranker with memory service."""

    def test_integration_with_search_result(self):
        """Test integration with SearchResult objects."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            mock_model = MagicMock()
            mock_model.compute_score.return_value = [0.9, 0.7]
            BGEReranker._model = mock_model

            reranker = BGEReranker()
            results = [
                SearchResult(
                    id="doc1",
                    content="Python is great for data science",
                    score=0.8,
                    metadata={"source": "blog", "date": "2024-01-01"}
                ),
                SearchResult(
                    id="doc2",
                    content="Java is used in enterprise applications",
                    score=0.7,
                    metadata={"source": "docs", "date": "2024-01-02"}
                ),
            ]

            reranked = reranker.rerank("data science with Python", results)

            assert len(reranked) == 2
            assert reranked[0].id == "doc1"
            assert reranked[0].score == 0.9
            assert reranked[0].metadata["source"] == "blog"

    def test_query_document_pair_format(self):
        """Test that query-document pairs are formatted correctly."""
        with patch('app.infra.search.vector_store.FlagReranker'):
            mock_model = MagicMock()
            mock_model.compute_score.return_value = [0.8]
            BGEReranker._model = mock_model

            reranker = BGEReranker()
            results = [
                SearchResult(id="1", content="Test content", score=0.5, metadata={})
            ]

            reranker.rerank("test query", results)

            # Verify the pairs format
            call_args = mock_model.compute_score.call_args
            pairs = call_args[0][0]
            assert pairs == [["test query", "Test content"]]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
