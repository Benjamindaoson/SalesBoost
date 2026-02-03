import pytest
import asyncio
from typing import List
from app.infra.search.vector_store import HybridSearchEngine, VectorStore, SearchResult

class MockVectorStore(VectorStore):
    def __init__(self, results: List[SearchResult]):
        self.results = results
        
    async def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        return self.results

@pytest.mark.asyncio
async def test_rrf_fusion():
    # Setup mock data
    # Doc A: Rank 1 in Vector, Rank 2 in Keyword
    # Doc B: Rank 2 in Vector, Rank 1 in Keyword
    # Doc C: Rank 3 in Vector, Not in Keyword
    
    doc_a = SearchResult(id="A", content="A")
    doc_b = SearchResult(id="B", content="B")
    doc_c = SearchResult(id="C", content="C")
    
    vec_store = MockVectorStore([doc_a, doc_b, doc_c])
    kw_store = MockVectorStore([doc_b, doc_a]) # B is first here
    
    k = 1 # Small k to make math easy
    # Score A: 1/(1+1) + 1/(1+2) = 0.5 + 0.33 = 0.833
    # Score B: 1/(1+2) + 1/(1+1) = 0.33 + 0.5 = 0.833
    # Wait, rank starts at 0 or 1?
    # Implementation: enumerate starts at 0. Formula: 1 / (k + rank + 1) usually?
    # Code: 1.0 / (self.rrf_k + rank + 1)
    # So Rank 0 -> 1/(1+0+1) = 0.5
    # Rank 1 -> 1/(1+1+1) = 0.33
    
    # Score A: 0.5 (vec rank 0) + 0.33 (kw rank 1) = 0.833
    # Score B: 0.33 (vec rank 1) + 0.5 (kw rank 0) = 0.833
    # Score C: 0.25 (vec rank 2) = 0.25
    
    engine = HybridSearchEngine(vec_store, kw_store, rrf_k=1)
    
    results = await engine.search("query", top_k=3)
    
    assert len(results) == 3
    assert results[0].score > 0.8
    assert results[1].score > 0.8
    # Order of A and B might be stable or depend on sort stability if scores equal
    # But C should be last
    assert results[2].id == "C"
    
    # Test default k=60
    engine_def = HybridSearchEngine(vec_store, kw_store) # default k=60
    results_def = await engine_def.search("query")
    # Score A: 1/61 + 1/62
    # Score B: 1/62 + 1/61
    assert abs(results_def[0].score - results_def[1].score) < 0.0001
