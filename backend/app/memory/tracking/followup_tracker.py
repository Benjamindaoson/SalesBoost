import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class FollowupManager:
    """
    Tracks and manages follow-up tasks.
    """
    
    def __init__(self):
        self._tasks: Dict[str, List[str]] = {}

    def sync_tasks(self, session_id: str, items: List[str], turn_number: int):
        logger.info(f"Syncing {len(items)} follow-up tasks for session {session_id}")
        if session_id not in self._tasks:
            self._tasks[session_id] = []
        self._tasks[session_id].extend(items)

    def get_pending_tasks(self, session_id: str) -> List[str]:
        return self._tasks.get(session_id, [])

followup_tracker = FollowupManager()
