from typing import Dict, Any


def evaluate_rag_quality(recall: float, precision: float, fusion: float) -> float:
    # Simple composite score between 0 and 1
    score = recall * 0.4 + precision * 0.4 + fusion * 0.2
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score
