import asyncio
import os
import uuid

from app.memory.storage.vector_store import VectorStore
from app.tools.retriever import KnowledgeRetrieverTool


async def main() -> int:
    token = f"RAG-SELFTEST-{uuid.uuid4().hex[:8]}"
    content = f"This is a minimal RAG self-test payload. token={token}"
    meta = {"source": "rag_selftest", "filename": "rag_selftest.txt"}
    doc_id = f"rag_selftest_{token}"

    store = VectorStore(collection_name="sales_knowledge")
    if store.client is None:
        print("RAG self-test: Qdrant unavailable; cannot run")
        return 1

    store.add_documents([content], [meta], [doc_id])

    tool = KnowledgeRetrieverTool(store)
    result = await tool.run({"query": token, "top_k": 3})
    hits = result.get("results") or []
    if not hits:
        print("RAG self-test failed: no hits returned")
        return 1

    combined = "\n".join([h.get("content", "") for h in hits])
    if token not in combined:
        print("RAG self-test failed: token not found in hits")
        return 1

    print("RAG self-test passed")
    print(f"Top hit id={hits[0].get('id')} score={hits[0].get('score')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
