"""
Production-Ready Distributed WebSocket Manager using Redis Pub/Sub

Features:
- Distributed message broadcasting across multiple server instances
- Automatic reconnection on Redis failures
- Background listener tasks for each connection
- Graceful error handling
- Connection lifecycle management
"""
import asyncio
import json
import logging
from typing import Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from core.config import get_settings
from core.redis import get_redis

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisConnectionManager:
    """
    Production-ready distributed WebSocket connection manager.
    
    Uses Redis Pub/Sub to broadcast messages across multiple server instances.
    Each connection has a dedicated Redis channel: `ws:channel:{user_id}`
    
    Architecture:
    1. Local connections stored in memory (per server instance)
    2. Messages published to Redis channels
    3. Background listeners forward Redis messages to local WebSocket connections
    4. Automatic reconnection on Redis failures
    """
    
    def __init__(self):
        self.local_connections: Dict[str, WebSocket] = {}
        self.listener_tasks: Dict[str, asyncio.Task] = {}
        self.redis_client = None
        self._redis_lock = asyncio.Lock()
        self._shutdown = False
        
    async def _ensure_redis(self):
        """Ensure Redis client is initialized and connected"""
        if self.redis_client is None:
            async with self._redis_lock:
                if self.redis_client is None:
                    try:
                        self.redis_client = await get_redis()
                        # Test connection (skip if InMemoryCache)
                        if hasattr(self.redis_client, 'ping'):
                            try:
                                await self.redis_client.ping()
                            except AttributeError:
                                # InMemoryCache doesn't have ping, that's OK
                                pass
                        logger.info("Redis client initialized for WebSocket manager")
                    except Exception as e:
                        logger.error(f"Failed to initialize Redis client: {e}")
                        raise
    
    def _is_redis_available(self) -> bool:
        """Check if real Redis is available (not InMemoryCache)"""
        if self.redis_client is None:
            return False
        # InMemoryCache doesn't have pubsub method
        return hasattr(self.redis_client, 'pubsub')
    
    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """
        Connect a WebSocket and start listening to Redis channel.
        
        Args:
            user_id: User identifier (used for Redis channel naming)
            websocket: FastAPI WebSocket connection
        """
        try:
            await websocket.accept()
            await self._ensure_redis()
            
            # Store local connection
            self.local_connections[user_id] = websocket
            
            # Start background listener task
            await self._start_listener(user_id, websocket)
            
            logger.info(f"WebSocket connected for user: {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket for user {user_id}: {e}")
            try:
                await websocket.close(code=1011, reason="Connection setup failed")
            except:
                pass
            raise
    
    async def disconnect(self, user_id: str) -> None:
        """
        Disconnect WebSocket and cleanup resources.
        
        Args:
            user_id: User identifier
        """
        try:
            # Stop listener task
            if user_id in self.listener_tasks:
                task = self.listener_tasks[user_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self.listener_tasks[user_id]
            
            # Remove local connection
            if user_id in self.local_connections:
                websocket = self.local_connections[user_id]
                try:
                    await websocket.close(code=1000, reason="Client disconnected")
                except:
                    pass
                del self.local_connections[user_id]
            
            logger.info(f"WebSocket disconnected for user: {user_id}")
            
        except Exception as e:
            logger.error(f"Error during disconnect for user {user_id}: {e}")
    
    async def subscribe_to_channel(self, user_id: str):
        """
        Subscribe to Redis channel for a user.
        This is called automatically by _start_listener.
        
        Args:
            user_id: User identifier
            
        Returns:
            PubSub object or None if Redis not available
        """
        await self._ensure_redis()
        
        # Check if Redis is available (not InMemoryCache)
        if not self._is_redis_available():
            logger.warning(
                "Redis Pub/Sub not available (using InMemoryCache). "
                "Distributed messaging will not work."
            )
            return None
        
        channel = self._get_channel_name(user_id)
        
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(channel)
            logger.debug(f"Subscribed to Redis channel: {channel}")
            return pubsub
        except Exception as e:
            logger.error(f"Failed to subscribe to channel {channel}: {e}")
            raise
    
    async def publish_message(self, user_id: str, message: dict) -> int:
        """
        Publish a message to Redis channel.
        
        Args:
            user_id: Target user identifier
            message: Message dictionary to send
            
        Returns:
            Number of subscribers that received the message (0 if Redis not available)
        """
        try:
            await self._ensure_redis()
            
            # Check if Redis is available (not InMemoryCache)
            if not self._is_redis_available():
                logger.debug(
                    "Redis Pub/Sub not available, message will only be sent to local connection"
                )
                return 0
            
            channel = self._get_channel_name(user_id)
            
            # Serialize message
            message_json = json.dumps(message, ensure_ascii=False)
            
            # Publish to Redis
            subscribers = await self.redis_client.publish(channel, message_json)
            
            logger.debug(
                f"Published message to channel {channel}, "
                f"subscribers: {subscribers}"
            )
            
            return subscribers
            
        except Exception as e:
            logger.error(f"Failed to publish message to user {user_id}: {e}")
            # Try to reconnect
            await self._reconnect_redis()
            raise
    
    async def send_json(self, user_id: str, data: dict) -> None:
        """
        Send JSON message via Redis Pub/Sub.
        This is the main method used by the application.
        
        Args:
            user_id: Target user identifier
            data: Message dictionary
        """
        try:
            # Always publish via Redis for distributed architecture
            await self.publish_message(user_id, data)
            
            # Also send directly if connection is local (optimization)
            # This reduces latency for local connections
            if user_id in self.local_connections:
                try:
                    websocket = self.local_connections[user_id]
                    await websocket.send_json(data)
                    logger.debug(f"Sent message directly to local connection: {user_id}")
                except Exception as e:
                    logger.warning(
                        f"Failed to send directly to local connection {user_id}: {e}. "
                        f"Message was still published to Redis."
                    )
                    
        except Exception as e:
            logger.error(f"Failed to send JSON to user {user_id}: {e}")
            raise
    
    async def _start_listener(self, user_id: str, websocket: WebSocket) -> None:
        """
        Start background task to listen to Redis channel and forward messages.
        
        Args:
            user_id: User identifier
            websocket: WebSocket connection to forward messages to
        """
        if user_id in self.listener_tasks:
            # Cancel existing task
            self.listener_tasks[user_id].cancel()
        
        # Create new listener task
        task = asyncio.create_task(
            self._listener_loop(user_id, websocket)
        )
        self.listener_tasks[user_id] = task
    
    async def _listener_loop(self, user_id: str, websocket: WebSocket) -> None:
        """
        Background task that listens to Redis channel and forwards messages.
        
        Args:
            user_id: User identifier
            websocket: WebSocket connection
        """
        channel = self._get_channel_name(user_id)
        pubsub = None
        reconnect_delay = 1.0
        max_reconnect_delay = 60.0
        
        while not self._shutdown:
            try:
                await self._ensure_redis()
                
                # Subscribe to channel
                pubsub = await self.subscribe_to_channel(user_id)
                
                # If Redis not available, exit listener (fallback to direct messaging)
                if pubsub is None:
                    logger.info(
                        f"Redis not available, listener loop exiting for user: {user_id}. "
                        f"Messages will be sent directly to local connection."
                    )
                    break
                
                # Reset reconnect delay on successful connection
                reconnect_delay = 1.0
                
                logger.info(f"Started listener loop for user: {user_id}, channel: {channel}")
                
                # Listen for messages
                async for message in pubsub.listen():
                    if self._shutdown:
                        break
                    
                    # Skip subscription confirmation messages
                    if message["type"] == "subscribe":
                        continue
                    
                    # Process actual messages
                    if message["type"] == "message":
                        try:
                            # Parse message
                            data = json.loads(message["data"])
                            
                            # Check if connection still exists
                            if user_id not in self.local_connections:
                                logger.warning(
                                    f"Received message for disconnected user: {user_id}"
                                )
                                break
                            
                            # Forward to WebSocket
                            current_websocket = self.local_connections.get(user_id)
                            if current_websocket and current_websocket == websocket:
                                await current_websocket.send_json(data)
                                logger.debug(
                                    f"Forwarded message from Redis to WebSocket: {user_id}"
                                )
                            else:
                                logger.warning(
                                    f"WebSocket mismatch for user {user_id}, "
                                    f"skipping message"
                                )
                                
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse Redis message: {e}")
                        except WebSocketDisconnect:
                            logger.info(f"WebSocket disconnected during listener loop: {user_id}")
                            break
                        except Exception as e:
                            logger.error(
                                f"Error forwarding message to WebSocket for user {user_id}: {e}"
                            )
                
            except asyncio.CancelledError:
                logger.info(f"Listener task cancelled for user: {user_id}")
                break
            except Exception as e:
                logger.error(
                    f"Listener loop error for user {user_id}: {e}, "
                    f"reconnecting in {reconnect_delay}s"
                )
                
                # Cleanup pubsub
                if pubsub:
                    try:
                        await pubsub.unsubscribe(channel)
                        await pubsub.close()
                    except:
                        pass
                    pubsub = None
                
                # Check if connection still exists
                if user_id not in self.local_connections:
                    logger.info(f"Connection removed, stopping listener for user: {user_id}")
                    break
                
                # Wait before reconnecting
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                
            finally:
                # Cleanup pubsub
                if pubsub:
                    try:
                        await pubsub.unsubscribe(channel)
                        await pubsub.close()
                    except:
                        pass
        
        logger.info(f"Listener loop ended for user: {user_id}")
    
    async def _reconnect_redis(self) -> None:
        """Reconnect to Redis"""
        async with self._redis_lock:
            try:
                if self.redis_client:
                    try:
                        if hasattr(self.redis_client, 'close'):
                            await self.redis_client.close()
                    except:
                        pass
                
                self.redis_client = None
                await self._ensure_redis()
                logger.info("Redis reconnected successfully")
                
            except Exception as e:
                logger.error(f"Failed to reconnect Redis: {e}")
    
    def _get_channel_name(self, user_id: str) -> str:
        """Get Redis channel name for a user"""
        return f"ws:channel:{user_id}"
    
    async def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.local_connections)
    
    async def is_connected(self, user_id: str) -> bool:
        """Check if a user is connected"""
        return user_id in self.local_connections
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the manager"""
        logger.info("Shutting down RedisConnectionManager...")
        self._shutdown = True
        
        # Disconnect all connections
        user_ids = list(self.local_connections.keys())
        for user_id in user_ids:
            await self.disconnect(user_id)
        
        # Close Redis connection
        if self.redis_client:
            try:
                if hasattr(self.redis_client, 'close'):
                    await self.redis_client.close()
            except:
                pass
        
        logger.info("RedisConnectionManager shutdown complete")


# Global instance
_manager: Optional[RedisConnectionManager] = None


def get_redis_connection_manager() -> RedisConnectionManager:
    """Get global RedisConnectionManager instance"""
    global _manager
    if _manager is None:
        _manager = RedisConnectionManager()
    return _manager


async def shutdown_redis_connection_manager() -> None:
    """Shutdown global RedisConnectionManager instance"""
    global _manager
    if _manager:
        await _manager.shutdown()
        _manager = None

