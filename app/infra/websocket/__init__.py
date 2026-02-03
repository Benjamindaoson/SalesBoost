"""
WebSocket Infrastructure Module

This module provides WebSocket connection management with support for:
- In-memory connection manager (single server)
- Redis-based distributed connection manager (horizontal scaling)

Usage:
    from app.infra.websocket import get_connection_manager

    manager = await get_connection_manager()
    await manager.connect(websocket, session_id, user_id)
    await manager.send_json(session_id, {"type": "message", "data": "..."})
    await manager.disconnect(session_id, user_id)
"""

from app.infra.websocket.manager_factory import (
    get_connection_manager,
    shutdown_connection_manager
)

__all__ = [
    "get_connection_manager",
    "shutdown_connection_manager"
]
