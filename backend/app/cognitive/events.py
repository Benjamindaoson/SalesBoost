from enum import Enum

class RoundEvent(str, Enum):
    START = "RoundStart"
    END = "RoundEnd"
    ABORT = "RoundAbort"
    TIMEOUT = "RoundTimeout"
    ERROR = "RoundError"
