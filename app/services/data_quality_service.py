import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Set, List

from app.services.knowledge_service import KnowledgeService
from app.services.graph_rag_service import GraphRAGService


class DataQualityService:
    """Compute quality metrics for vector store + GraphRAG."""

    def __init__(self, report_dir: str = "reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)
        self.ks = KnowledgeService()
        self.gr = GraphRAGService()

    def _vector_docs(self, limit: int = 5000) -> List[Dict[str, Any]]:
        return self.ks.list_documents(limit=limit)

    def _graph_ids(self) -> Set[str]:
        ids: Set[str] = set()
        for node_id, data in self.gr.knowledge_graph.graph.nodes(data=True):
            ids.add(str(node_id))
            for key in ["doc_id", "doc_ids", "source_doc_ids"]:
                val = data.get(key)
                if isinstance(val, list):
                    ids.update(str(v) for v in val)
                elif val:
                    ids.add(str(val))
        return {i for i in ids if i}

    def compute(self, write_files: bool = False) -> Dict[str, Any]:
        docs = self._vector_docs()
        total = len(docs)
        hashes: Dict[str, int] = {}
        duplicate_docs = 0
        completeness_hits = 0
        required_fields = ["source", "semantic_type", "section_path"]

        vector_ids: Set[str] = set()
        for doc in docs:
            content = doc.get("content", "") or ""
            doc_id = doc.get("id")
            meta = doc.get("metadata", {}) or {}
            h = hashlib.sha256(content.encode("utf-8")).hexdigest()
            hashes[h] = hashes.get(h, 0) + 1
            vector_ids.add(str(doc_id))
            for key in ["chunk_id", "doc_sha256", "source", "section_path"]:
                if key in meta:
                    vector_ids.add(str(meta[key]))

            if content.strip() and all(meta.get(f) for f in required_fields):
                completeness_hits += 1

        duplicate_docs = sum(count - 1 for count in hashes.values() if count > 1)
        duplication_rate = (duplicate_docs / total) if total else 0
        completeness_score = (completeness_hits / total) if total else 0

        graph_ids = self._graph_ids()
        union_total = max(1, len(vector_ids | graph_ids))
        drift_count = len(vector_ids.symmetric_difference(graph_ids))
        consistency_score = 1 - drift_count / union_total

        metrics = {
            "total_documents": total,
            "duplicate_docs": duplicate_docs,
            "duplication_rate": round(duplication_rate, 4),
            "completeness_score": round(completeness_score, 4),
            "consistency_score": round(consistency_score, 4),
            "drift_missing_in_graph": sorted(list(vector_ids - graph_ids))[:50],
            "drift_missing_in_vector": sorted(list(graph_ids - vector_ids))[:50],
        }

        markdown = self._markdown(metrics)
        if write_files:
            (self.report_dir / "data_quality_report.json").write_text(
                json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            (self.report_dir / "data_quality_report.md").write_text(markdown, encoding="utf-8")
        metrics["markdown"] = markdown
        return metrics

    def _markdown(self, m: Dict[str, Any]) -> str:
        return f"""# Data Quality Report

- Total documents: {m['total_documents']}
- Completeness score: {m['completeness_score'] * 100:.2f}%
- Consistency score (Vector vs Graph): {m['consistency_score'] * 100:.2f}%
- Duplication rate: {m['duplication_rate'] * 100:.2f}%

## Drift Details
- Missing in Graph (sample): {m['drift_missing_in_graph']}
- Missing in Vector (sample): {m['drift_missing_in_vector']}
"""


data_quality_service = DataQualityService()

__all__ = ["data_quality_service", "DataQualityService"]
