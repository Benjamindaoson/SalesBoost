class SimpleAuditGate:
    """
    Enhanced Audit Gate for Production Safety.
    """
    
    SENSITIVE_WORDS = [
        "scam", "fraud", "100% return", "guaranteed profit", 
        "credit card", "ssn", "social security", "password"
    ]
    
    INJECTION_PATTERNS = [
        "ignore previous instructions", 
        "system prompt", 
        "simulated mode", 
        "unrestricted mode"
    ]

    def check(self, text: str, meta: dict) -> bool:
        text_lower = text.lower()
        
        # 1. Check for sensitive/banned content
        if any(x in text_lower for x in self.SENSITIVE_WORDS):
            return False
            
        # 2. Check for Prompt Injection
        if self._check_injection(text_lower):
            return False
            
        return True
        
    def _check_injection(self, text: str) -> bool:
        return any(x in text for x in self.INJECTION_PATTERNS)
