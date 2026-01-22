import logging
import re
from typing import Dict, List, Tuple

from app.security.prompt_guard import prompt_guard

logger = logging.getLogger(__name__)


PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"\b1[3-9]\d{9}\b"),
    "id_card": re.compile(r"\b\d{17}[\dXx]\b"),
}


def scrub_pii(text: str) -> Tuple[str, List[str]]:
    findings = []
    sanitized = text
    for label, pattern in PII_PATTERNS.items():
        if pattern.search(sanitized):
            findings.append(label)
            sanitized = pattern.sub(f"[REDACTED:{label}]", sanitized)
    return sanitized, findings


def sanitize_documents(results: List[Dict]) -> List[Dict]:
    sanitized_results = []
    for item in results:
        content = item.get("content", "")
        safe, reason = prompt_guard.detect(content)
        sanitized, pii = scrub_pii(content)
        metadata = dict(item.get("metadata", {}))
        if not safe:
            logger.warning("Prompt injection detected in retrieved content: %s", reason)
            metadata["injection_flag"] = reason
            sanitized = "[CONTENT REDACTED DUE TO PROMPT INJECTION]"
        if pii:
            metadata["pii_redacted"] = pii
        sanitized_results.append({**item, "content": sanitized, "metadata": metadata})
    return sanitized_results
