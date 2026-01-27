from typing import Dict, Any


class KnowledgeEngine:
    def __init__(self):
        self.sources = []

    def inject(self, source: str, data: Dict[str, Any]) -> str:
        entry_id = f"ke_{len(self.sources) + 1}"
        self.sources.append({"id": entry_id, "source": source, "data": data})
        return entry_id

    def fetch(self, entry_id: str) -> Dict[str, Any]:
        for s in self.sources:
            if s["id"] == entry_id:
                return s
        return {}
