import logging
from app.infra.events.bus import bus
from app.infra.events.schemas import EventType, MemoryEventPayload
from app.services.memory_event_writer import record_event

logger = logging.getLogger(__name__)

class MemoryPersistenceService:
    """
    Subscribes to memory events and persists them to the database.
    """
    
    @staticmethod
    @bus.subscribe(EventType.MEMORY_EVENT_RECORDED)
    async def handle_memory_event(payload_dict: dict):
        # Redis bus sends dict, Memory bus sends object.
        # Ensure we have a dict to work with or handle both.
        if isinstance(payload_dict, dict):
            payload = MemoryEventPayload(**payload_dict)
        else:
            payload = payload_dict

        logger.info(f"Persisting memory event: {payload.event_id}")
        try:
            await record_event(payload)
            logger.debug(f"Memory event saved: {payload.event_id}")
        except Exception as e:
            logger.error(f"Failed to save memory event: {e}")

# Initialize service to register subscribers
memory_persistence_service = MemoryPersistenceService()
