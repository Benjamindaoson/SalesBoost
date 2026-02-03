"""
WebSocket heartbeat manager for session monitoring and suspension.
Implements bidirectional heartbeat with timeout detection and automatic session suspension.
"""
import asyncio
import logging
import time
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatConfig:
    """Configuration for heartbeat monitoring."""
    ping_interval: float = 30.0  # Send ping every 30 seconds
    pong_timeout: float = 10.0   # Wait 10 seconds for pong response
    max_missed_pongs: int = 3    # Suspend after 3 missed pongs
    
    
@dataclass
class SessionHealth:
    """Health status of a WebSocket session."""
    session_id: str
    last_ping_sent: float
    last_pong_received: float
    missed_pongs: int = 0
    is_suspended: bool = False
    suspension_reason: Optional[str] = None


class HeartbeatManager:
    """
    Manages WebSocket heartbeat monitoring and session suspension.
    
    Implements bidirectional heartbeat mechanism with:
    - Automatic ping sending at configured intervals
    - Pong timeout detection
    - Session suspension on heartbeat failure
    - FSM state snapshot creation on suspension
    
    Example:
        >>> manager = HeartbeatManager()
        >>> await manager.start_monitoring(session_id, websocket, on_suspend_callback)
        >>> await manager.record_pong(session_id)
        >>> await manager.stop_monitoring(session_id)
    """
    
    def __init__(self, config: Optional[HeartbeatConfig] = None):
        """
        Initialize heartbeat manager.
        
        Args:
            config: Heartbeat configuration, uses defaults if None
        """
        self.config = config or HeartbeatConfig()
        self._session_health: Dict[str, SessionHealth] = {}
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._on_suspend_callbacks: Dict[str, Callable] = {}
        
    async def start_monitoring(
        self,
        session_id: str,
        websocket,
        on_suspend: Optional[Callable] = None
    ) -> None:
        """
        Start heartbeat monitoring for a session.
        
        Args:
            session_id: Unique session identifier
            websocket: WebSocket connection object
            on_suspend: Optional callback function to call on suspension
        """
        if session_id in self._monitoring_tasks:
            logger.warning(f"Heartbeat monitoring already active for session: {session_id}")
            return
        
        # Initialize session health
        now = time.time()
        self._session_health[session_id] = SessionHealth(
            session_id=session_id,
            last_ping_sent=now,
            last_pong_received=now
        )
        
        if on_suspend:
            self._on_suspend_callbacks[session_id] = on_suspend
        
        # Start monitoring task
        task = asyncio.create_task(self._heartbeat_loop(session_id, websocket))
        self._monitoring_tasks[session_id] = task
        
        logger.info(f"Started heartbeat monitoring for session: {session_id}")
    
    async def stop_monitoring(self, session_id: str) -> None:
        """
        Stop heartbeat monitoring for a session.
        
        Args:
            session_id: Session to stop monitoring
        """
        if session_id in self._monitoring_tasks:
            self._monitoring_tasks[session_id].cancel()
            self._monitoring_tasks.pop(session_id, None)
        
        self._session_health.pop(session_id, None)
        self._on_suspend_callbacks.pop(session_id, None)
        
        logger.info(f"Stopped heartbeat monitoring for session: {session_id}")
    
    async def record_pong(self, session_id: str) -> None:
        """
        Record pong response from client.
        
        Args:
            session_id: Session that sent pong
        """
        if session_id in self._session_health:
            health = self._session_health[session_id]
            health.last_pong_received = time.time()
            health.missed_pongs = 0
            logger.debug(f"Pong received from session: {session_id}")
    
    def get_session_health(self, session_id: str) -> Optional[SessionHealth]:
        """
        Get health status for a session.
        
        Args:
            session_id: Session to query
            
        Returns:
            SessionHealth object or None if not monitored
        """
        return self._session_health.get(session_id)
    
    async def _heartbeat_loop(self, session_id: str, websocket) -> None:
        """
        Background task for sending pings and monitoring pongs.
        
        Args:
            session_id: Session to monitor
            websocket: WebSocket connection
        """
        try:
            while True:
                await asyncio.sleep(self.config.ping_interval)
                
                health = self._session_health.get(session_id)
                if not health:
                    break
                
                # Send ping
                try:
                    await websocket.send_json({"type": "ping", "timestamp": time.time()})
                    health.last_ping_sent = time.time()
                    logger.debug(f"Ping sent to session: {session_id}")
                except Exception as e:
                    logger.error(f"Failed to send ping to session {session_id}: {e}")
                    await self._suspend_session(session_id, f"Ping send failed: {e}")
                    break
                
                # Check for pong timeout
                time_since_pong = time.time() - health.last_pong_received
                if time_since_pong > (self.config.ping_interval + self.config.pong_timeout):
                    health.missed_pongs += 1
                    logger.warning(
                        f"Missed pong from session {session_id}. "
                        f"Count: {health.missed_pongs}/{self.config.max_missed_pongs}"
                    )
                    
                    if health.missed_pongs >= self.config.max_missed_pongs:
                        await self._suspend_session(
                            session_id,
                            f"Heartbeat timeout: {health.missed_pongs} missed pongs"
                        )
                        break
                        
        except asyncio.CancelledError:
            logger.info(f"Heartbeat monitoring cancelled for session: {session_id}")
        except Exception as e:
            logger.error(f"Heartbeat loop error for session {session_id}: {e}")
            await self._suspend_session(session_id, f"Heartbeat loop error: {e}")
    
    async def _suspend_session(self, session_id: str, reason: str) -> None:
        """
        Suspend a session due to heartbeat failure.
        
        Args:
            session_id: Session to suspend
            reason: Reason for suspension
        """
        health = self._session_health.get(session_id)
        if health:
            health.is_suspended = True
            health.suspension_reason = reason
        
        logger.warning(f"Session suspended: {session_id}. Reason: {reason}")
        
        # Call suspension callback if registered
        if session_id in self._on_suspend_callbacks:
            try:
                await self._on_suspend_callbacks[session_id](session_id, reason)
            except Exception as e:
                logger.error(f"Suspension callback failed for session {session_id}: {e}")
        
        # Stop monitoring
        await self.stop_monitoring(session_id)


# Global heartbeat manager instance
heartbeat_manager = HeartbeatManager()
