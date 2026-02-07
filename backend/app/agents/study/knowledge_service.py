"""Knowledge service stub."""
from __future__ import annotations

import uuid


class KnowledgeService:
    _docs: dict = {}

    def add_document(self, content: str, metadata: dict) -> str:
        doc_id = str(uuid.uuid4())
        self._docs[doc_id] = {"content": content, "metadata": metadata}
        return doc_id

    def count_documents(self) -> int:
        return len(self._docs)
