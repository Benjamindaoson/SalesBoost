from __future__ import annotations

import re
from typing import Dict, List, Tuple


def compute_quality(query: str, results: List[Dict]) -> Tuple[float, Dict[str, float]]:
    """
    计算检索质量：
    - 置信度 (score_avg)
    - 覆盖率 (coverage)
    """
    if not results:
        return 0.0, {"score_avg": 0.0, "coverage": 0.0}

    scores = []
    for item in results:
        score = item.get("rerank_score", item.get("relevance_score", item.get("score", 0.0)))
        scores.append(float(score))
    score_avg = sum(scores) / max(len(scores), 1)

    query_terms = _tokenize(query)
    covered_terms = set()
    for item in results:
        content = item.get("content", "")
        covered_terms |= query_terms.intersection(_tokenize(content))
    coverage = len(covered_terms) / max(len(query_terms), 1)

    quality = 0.6 * score_avg + 0.4 * coverage
    return quality, {"score_avg": score_avg, "coverage": coverage}


def should_retry(quality: float, stats: Dict[str, float]) -> bool:
    return quality < 0.55 or stats.get("coverage", 0.0) < 0.4


def _tokenize(text: str) -> set[str]:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text.lower())
    tokens = {t.strip() for t in cleaned.split() if t.strip()}
    return tokens
