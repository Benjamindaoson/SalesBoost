import logging
import re


class SensitiveDataFilter(logging.Filter):
    """Mask sensitive data in log records to avoid leaking secrets."""

    SENSITIVE_PATTERNS = [
        re.compile(r"(Authorization:\s*Bearer\s+)([^\s]+)", re.IGNORECASE),
        re.compile(r"(X-Api-Key:\s*)([^\s]+)", re.IGNORECASE),
        re.compile(r"(Cookie:\s*)([^;\n]+)", re.IGNORECASE),
        re.compile(r"(Set-Cookie:\s*)([^;\n]+)", re.IGNORECASE),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if not isinstance(msg, str):
            return True
        for pat in self.SENSITIVE_PATTERNS:
            msg = pat.sub(r"\1******", msg)
        try:
            record.msg = msg
        except Exception:
            pass
        return True
