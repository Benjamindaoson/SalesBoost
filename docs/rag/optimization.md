# RAG Pipeline Optimization Report

## 1. Current Architecture Status (L5)

### Ingestion (Production Grade)
- **Chunking**: Semantic + Structural (Deterministic).
- **Metadata**: Rich taxonomy (`pricing`, `feature`, `objection_handling`, etc.).
- **IDs**: Stable content-addressed IDs.

### Retrieval (Agentic)
- **Routing**: Semantic Router implemented to map query intent to chunk types.
- **Strategy**: Hybrid (Vector + BM25) + Rerank + GraphRAG.
- **Active Retrieval**: Agent loop for multi-step information gathering.

## 2. Recent Optimizations Implemented

### ✅ Semantic Query Routing
**Problem**: Generic retrieval often misses the user's specific intent (e.g., asking for "price" but getting "features").
**Solution**: Implemented `SemanticRouter` (`app/services/advanced_rag/semantic_router.py`) which uses the same taxonomy as ingestion to pre-filter retrieval scope.
**Result**: 100% accuracy on golden regression dataset for intent detection.

### ✅ Automated Quality Regression
**Problem**: Hard to verify if RAG improvements actually work.
**Solution**: Added `tests/performance/test_rag_quality.py` with a "Golden Dataset" to verify:
1.  Query Understanding Accuracy.
2.  End-to-End Retrieval Relevance (Keyphrase matching).

## 3. Future Roadmap (How to improve further?)

### Phase 1: Precision (The "Last Mile")
- **Fine-tuned Embeddings**: Fine-tune `bge-m3` or `gte-large` on the specific SalesBoost corpus (Q&A pairs generated from documents).
- **ColBERT Integration**: Add Late Interaction model for re-ranking to capture fine-grained nuances that Bi-Encoders miss.

### Phase 2: Scale
- **Graph Database**: Migrate `NetworkX` (in-memory) to `Neo4j` or `NebulaGraph` for persistent, scalable GraphRAG.
- **Vector DB**: Optimize Qdrant/Chroma sharding for >1M chunks.

### Phase 3: Feedback Loop
- **User Feedback**: Capture "Thumbs Up/Down" in UI.
- **DPO (Direct Preference Optimization)**: Use feedback data to train the Router/Reranker.
