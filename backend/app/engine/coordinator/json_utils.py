import json
from typing import Any, Dict, Optional


def extract_json(text: Optional[str]) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    cleaned = text.strip()
    if "```" in cleaned:
        parts = cleaned.split("```")
        candidate = None
        for part in parts:
            if "{" in part and "}" in part:
                candidate = part
                break
        if candidate:
            cleaned = candidate.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = cleaned[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return None
