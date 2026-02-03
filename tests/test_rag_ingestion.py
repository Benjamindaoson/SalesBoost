import pytest
import os
import shutil
import asyncio
from cognitive.skills.study.knowledge_service import KnowledgeService

# Use a temporary directory for ChromaDB in tests
TEST_CHROMA_DIR = "./chroma_db_test"

@pytest.fixture
def knowledge_service():
    # Setup
    if os.path.exists(TEST_CHROMA_DIR):
        shutil.rmtree(TEST_CHROMA_DIR)
    
    # Override settings if possible, but KnowledgeService uses global settings.
    # We will assume it uses default or env vars. 
    # For now, we just instantiate it. 
    # Note: If it persists to disk, we might want to clean up after.
    service = KnowledgeService()
    # Mocking or configuring path would be better, but let's test the real service.
    
    yield service
    
    # Teardown
    # Note: Chroma might hold file locks. 
    pass

def test_rag_ingestion_and_retrieval(knowledge_service):
    """
    P1: RAG Ingestion & Consumption Loop
    """
    # 1. Ingest Text
    doc_id = knowledge_service.add_document(
        content="SalesBoost is the best sales training platform in 2026.",
        metadata={"source": "manual", "type": "product_info"}
    )
    assert doc_id is not None
    print(f"Document added: {doc_id}")
    
    # 2. Query
    results = knowledge_service.query("What is SalesBoost?", top_k=1)
    
    # 3. Verify
    assert len(results) > 0
    top_result = results[0]
    print(f"Top result: {top_result}")
    
    assert "SalesBoost" in top_result["content"]
    assert top_result["metadata"]["source"] == "manual"
    
    # 4. Ingest Another (PDF Simulation)
    doc_id_2 = knowledge_service.add_document(
        content="Handling Price Objection: Focus on value, not cost. ROI is key.",
        metadata={"source": "objection_handling.pdf", "type": "strategy"}
    )
    
    # 5. Query Strategy
    results_strat = knowledge_service.query("How to handle price objection?", top_k=1)
    assert len(results_strat) > 0
    assert "ROI" in results_strat[0]["content"]
    
    print("\n✅ RAG Verification Passed: Ingestion -> Vector -> Retrieval works.")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
