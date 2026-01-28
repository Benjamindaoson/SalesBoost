from typing import List, Dict
from app.memory.storage.vector_store import VectorStore

class Retriever:
    def __init__(self, vector_store=None):
        self.vector_store = vector_store or VectorStore()

    def retrieve(self, query: str, top_k: int = 3) -> str:
        hits = self.vector_store.query(query, n_results=top_k)
        if not hits:
            return ""
            
        # Format context for LLM
        context_parts = []
        for hit in hits:
            content = hit.get("content", "")
            meta = hit.get("metadata", {})
            source = meta.get("filename", "unknown")
            context_parts.append(f"[{source}]: {content}")
            
        return "\n\n".join(context_parts)
