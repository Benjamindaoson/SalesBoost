"""
WebSocket Connection Manager Factory

This module provides a factory function to create the appropriate connection manager
based on configuration.

Supported Managers:
- InMemoryConnectionManager: Original implementation (single server only)
- RedisConnectionManager: Distributed implementation (horizontal scaling)

Configuration:
Set WEBSOCKET_MANAGER_TYPE in environment:
- "memory" (default): Use in-memory manager
- "redis": Use Redis-based distributed manager

Example:
    from app.infra.websocket.manager_factory import get_connection_manager

    manager = await get_connection_manager()
    await manager.connect(websocket, session_id, user_id)
"""

import logging
from typing import Optional

from core.config import get_settings

logger = logging.getLogger(__name__)

_manager_instance: Optional[any] = None


async def get_connection_manager():
    """
    Get or create connection manager instance (singleton)

    Returns:
        Connection manager instance (InMemoryConnectionManager or RedisConnectionManager)
    """
    global _manager_instance

    if _manager_instance is not None:
        return _manager_instance

    settings = get_settings()
    manager_type = getattr(settings, 'WEBSOCKET_MANAGER_TYPE', 'memory')

    if manager_type == 'redis':
        logger.info("[ConnectionManagerFactory] Creating RedisConnectionManager")
        from app.infra.websocket.redis_connection_manager import RedisConnectionManager

        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        manager = RedisConnectionManager(redis_url=redis_url)
        await manager.initialize()
        _manager_instance = manager

    else:
        logger.info("[ConnectionManagerFactory] Creating InMemoryConnectionManager")
        # Import the original ConnectionManager from websocket.py
        # For now, we'll keep it in websocket.py and import it
        # In Phase 3.2, we'll extract it to a separate module
        from api.endpoints.websocket import ConnectionManager as InMemoryConnectionManager
        _manager_instance = InMemoryConnectionManager()

    return _manager_instance


async def shutdown_connection_manager():
    """Shutdown connection manager (cleanup resources)"""
    global _manager_instance

    if _manager_instance is not None:
        if hasattr(_manager_instance, 'shutdown'):
            await _manager_instance.shutdown()
        _manager_instance = None
        logger.info("[ConnectionManagerFactory] Connection manager shutdown complete")
