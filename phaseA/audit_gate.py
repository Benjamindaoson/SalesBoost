import time
from typing import Optional, Dict, Any, Tuple

class AuditGate:
    """
    Simple streaming output audit gate skeleton.
    - audit(content, metadata=None) -> (allowed: bool, audit_record: dict)
    - Uses metadata.get('restricted_keywords', []) to decide allowed
    - Logs audits for later review
    """
    def __init__(self):
        self.records = []

    def audit(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
        if metadata is None:
            metadata = {}
        restricted = metadata.get("restricted_keywords", [])
        allowed = not any(r in content for r in restricted)
        rec = {
            "content_preview": content[:100],
            "allowed": allowed,
            "restricted_keywords": restricted,
            "timestamp": time.time(),
            "metadata": metadata
        }
        self.records.append(rec)
        return allowed, rec
