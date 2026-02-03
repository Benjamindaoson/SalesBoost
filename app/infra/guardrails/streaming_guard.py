import logging
from typing import AsyncGenerator, List
import re

logger = logging.getLogger(__name__)

class StreamingGuard:
    """
    Guardrail for streaming output.
    Ensures that content is vetted before being sent to the user.
    """
    
    def __init__(self, sensitive_patterns: List[str] = None):
        self.sensitive_patterns = sensitive_patterns or [
            r"ignore all previous instructions",
            r"system prompt",
            r"password",
            r"api key"
        ]
        self._compiled_patterns = [re.compile(p, re.I) for p in self.sensitive_patterns]

    async def audit_stream(self, stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        """
        Audit a stream of text chunks.
        In MVP, we use a simple buffer to check for sensitive patterns.
        """
        buffer = ""
        async for chunk in stream:
            buffer += chunk
            
            # Simple check: if buffer gets too large or contains sensitive info, block it
            is_unsafe = False
            for pattern in self._compiled_patterns:
                if pattern.search(buffer):
                    logger.warning(f"Sensitive pattern detected in stream: {pattern.pattern}")
                    is_unsafe = True
                    break
            
            if is_unsafe:
                yield "[CONTENT BLOCKED FOR COMPLIANCE]"
                return
            
            # Yield the chunk if safe
            yield chunk
            
            # Keep buffer small to avoid memory issues
            if len(buffer) > 1000:
                buffer = buffer[-500:]

streaming_guard = StreamingGuard()
