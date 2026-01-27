from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any
import time


class RoundEventType(Enum):
    ROUND_START = "ROUND_START"
    ROUND_END = "ROUND_END"
    ABORT = "ABORT"


@dataclass
class RoundEvent:
    event_type: RoundEventType
    round_id: str
    timestamp: float
    details: Dict[str, Any]


def create_round_event(event_type: RoundEventType, round_id: str, details: Dict[str, Any] = None) -> RoundEvent:
    if details is None:
        details = {}
    return RoundEvent(event_type=event_type, round_id=round_id, timestamp=time.time(), details=details)
