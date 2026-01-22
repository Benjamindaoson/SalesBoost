# Redis WebSocket Manager Usage Guide

## Overview

The `RedisConnectionManager` is a production-ready distributed WebSocket manager that uses Redis Pub/Sub to broadcast messages across multiple server instances.

## Features

- ✅ **Distributed Broadcasting**: Messages published to Redis channels reach all server instances
- ✅ **Automatic Reconnection**: Handles Redis connection failures gracefully
- ✅ **Background Listeners**: Each connection has a dedicated listener task
- ✅ **Connection Management**: Tracks local WebSocket connections
- ✅ **Error Handling**: Robust error handling with retry logic

## Architecture

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Server 1   │         │  Server 2   │         │  Server 3   │
│             │         │             │         │             │
│  WS Client A │         │  WS Client B │         │  WS Client C │
│      │       │         │      │       │         │      │       │
│      └───────┼─────────┼───────┼───────┼─────────┼───────┘
│              │         │       │       │         │
│  Local       │         │  Local│       │         │  Local
│  Connections │         │  Connections │         │  Connections
│              │         │       │       │         │
└──────┬───────┘         └───────┼───────┘         └───────┬───────┘
       │                        │                        │
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Redis Pub/Sub       │
                    │                       │
                    │  ws:channel:{user_id} │
                    └───────────────────────┘
```

## Usage

### Basic Setup

```python
from app.core.redis_manager import get_redis_connection_manager

# Get the global manager instance
manager = get_redis_connection_manager()
```

### Connect a WebSocket

```python
from fastapi import WebSocket

@app.websocket("/ws/train")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    # Connect the WebSocket
    await manager.connect(user_id, websocket)
    
    try:
        # Your WebSocket logic here
        while True:
            data = await websocket.receive_json()
            # Process data...
            
    except WebSocketDisconnect:
        pass
    finally:
        # Disconnect when done
        await manager.disconnect(user_id)
```

### Send Messages

```python
# Send a message (automatically published to Redis)
await manager.send_json(
    user_id="user123",
    data={
        "type": "message",
        "content": "Hello, World!"
    }
)
```

### Integration with Existing Code

Replace the existing `ConnectionManager` in `websocket.py`:

```python
# Old code
from app.core.redis_manager import ConnectionManager

# New code
from app.core.redis_manager import get_redis_connection_manager

manager = get_redis_connection_manager()

# Usage remains the same
await manager.connect(user_id, websocket)
await manager.send_json(user_id, data)
await manager.disconnect(user_id)
```

## API Reference

### `connect(user_id: str, websocket: WebSocket) -> None`

Connect a WebSocket and start listening to Redis channel.

**Parameters**:
- `user_id`: User identifier (used for Redis channel naming)
- `websocket`: FastAPI WebSocket connection

**Raises**:
- `Exception`: If connection setup fails

### `disconnect(user_id: str) -> None`

Disconnect WebSocket and cleanup resources.

**Parameters**:
- `user_id`: User identifier

### `send_json(user_id: str, data: dict) -> None`

Send JSON message via Redis Pub/Sub.

**Parameters**:
- `user_id`: Target user identifier
- `data`: Message dictionary

**Behavior**:
- Always publishes to Redis for distributed architecture
- Also sends directly to local connection if available (optimization)

### `publish_message(user_id: str, message: dict) -> int`

Publish a message to Redis channel.

**Parameters**:
- `user_id`: Target user identifier
- `message`: Message dictionary

**Returns**:
- Number of subscribers that received the message

### `subscribe_to_channel(user_id: str) -> None`

Subscribe to Redis channel for a user (called automatically).

### `is_connected(user_id: str) -> bool`

Check if a user is connected.

**Returns**:
- `True` if user has active connection, `False` otherwise

### `get_connection_count() -> int`

Get number of active connections.

**Returns**:
- Number of active connections

### `shutdown() -> None`

Gracefully shutdown the manager (cleanup all connections and Redis).

## Channel Naming

Channels are named using the pattern: `ws:channel:{user_id}`

Example:
- User ID: `user123` → Channel: `ws:channel:user123`

## Error Handling

The manager handles various error scenarios:

1. **Redis Connection Failures**: Automatic reconnection with exponential backoff
2. **WebSocket Disconnections**: Cleanup of resources and listener tasks
3. **Message Parsing Errors**: Logged and skipped
4. **Connection Mismatches**: Detected and handled gracefully

## Performance Considerations

1. **Local Optimization**: Messages are sent directly to local connections when available
2. **Background Tasks**: Each connection has a dedicated listener task
3. **Connection Pooling**: Redis client is reused across connections
4. **Graceful Degradation**: Falls back gracefully if Redis is unavailable

## Migration from ConnectionManager

### Step 1: Update Imports

```python
# Old
from app.api.endpoints.websocket import ConnectionManager
manager = ConnectionManager()

# New
from app.core.redis_manager import get_redis_connection_manager
manager = get_redis_connection_manager()
```

### Step 2: Update Method Signatures

The API is compatible, but note:
- `connect()` now takes `user_id` first, then `websocket`
- `send_json()` uses `user_id` instead of `session_id`

### Step 3: Update WebSocket Endpoint

```python
# Old
await manager.connect(websocket, session_id, db)

# New
await manager.connect(user_id, websocket)
# Store db separately if needed
```

## Testing

```python
import pytest
from app.core.redis_manager import get_redis_connection_manager

@pytest.mark.asyncio
async def test_redis_connection_manager():
    manager = get_redis_connection_manager()
    
    # Mock WebSocket
    websocket = MockWebSocket()
    
    # Connect
    await manager.connect("user123", websocket)
    assert await manager.is_connected("user123")
    
    # Send message
    await manager.send_json("user123", {"type": "test"})
    
    # Disconnect
    await manager.disconnect("user123")
    assert not await manager.is_connected("user123")
```

## Production Considerations

1. **Redis Configuration**: Ensure Redis is properly configured in `config.py`
2. **Connection Limits**: Monitor Redis connection pool size
3. **Channel Cleanup**: Channels are automatically cleaned up on disconnect
4. **Graceful Shutdown**: Call `shutdown()` on application exit
5. **Monitoring**: Monitor Redis Pub/Sub message rates and connection counts

## Troubleshooting

### Redis Connection Issues

If Redis is unavailable, the manager will:
1. Log errors
2. Attempt reconnection with exponential backoff
3. Continue operating (messages may be delayed)

### Message Not Received

Check:
1. User is connected (`is_connected()`)
2. Redis channel name is correct (`ws:channel:{user_id}`)
3. Redis Pub/Sub is working (`redis-cli PUBSUB CHANNELS`)
4. Listener task is running (check logs)

### High Memory Usage

Monitor:
1. Number of active connections
2. Listener task count
3. Redis connection pool size

## Example: Full Integration

```python
from fastapi import WebSocket, WebSocketDisconnect
from app.core.redis_manager import get_redis_connection_manager

manager = get_redis_connection_manager()

@app.websocket("/ws/train")
async def websocket_training(
    websocket: WebSocket,
    user_id: str = Query(...),
):
    try:
        # Connect
        await manager.connect(user_id, websocket)
        
        # Send welcome message
        await manager.send_json(user_id, {
            "type": "welcome",
            "message": "Connected successfully"
        })
        
        # Message loop
        while True:
            data = await websocket.receive_json()
            
            # Process message
            response = await process_message(data)
            
            # Send response
            await manager.send_json(user_id, response)
            
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {user_id}")
    finally:
        await manager.disconnect(user_id)
```


