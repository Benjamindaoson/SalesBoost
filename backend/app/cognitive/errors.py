class CognitiveError(Exception):
    pass

class TimeoutError(CognitiveError):
    pass

class AuditBlockedError(CognitiveError):
    pass
