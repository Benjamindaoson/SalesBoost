import asyncio
import logging
import time
import uuid
import json
import os
from typing import Dict, List, Callable, Any, Awaitable, Union, Optional
from app.infra.events.schemas import EventType, EventBase
from app.observability.tracing.execution_tracer import trace_manager
from redis import asyncio as aioredis
from redis.exceptions import ConnectionError

logger = logging.getLogger(__name__)

SubscriberFunc = Callable[[Any], Awaitable[None]]

class EventBus:
    """Abstract Event Bus"""
    def subscribe(self, event_type: Union[EventType, str]):
        raise NotImplementedError
    
    async def publish(self, event_type: Union[EventType, str], payload: Any):
        raise NotImplementedError

    async def request(self, event_type: EventType, payload: Any, timeout: float = 10.0) -> Any:
        raise NotImplementedError

class MemoryEventBus(EventBus):
    """
    In-Memory implementation (Legacy/Dev)
    """
    def __init__(self):
        self._subscribers: Dict[Union[EventType, str], List[SubscriberFunc]] = {}
        for t in EventType:
            self._subscribers[t] = []

    def subscribe(self, event_type: Union[EventType, str]):
        def decorator(func: SubscriberFunc):
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if func not in self._subscribers[event_type]:
                self._subscribers[event_type].append(func)
                logger.info(f"Registered subscriber {func.__name__} for event {event_type}")
            return func
        return decorator

    async def request(self, event_type: EventType, payload: Any, timeout: float = 10.0) -> Any:
        future = asyncio.get_event_loop().create_future()
        event_id = getattr(payload, 'event_id', str(uuid.uuid4()))
        response_event_type = f"response.{event_type}.{event_id}"
        
        @self.subscribe(response_event_type)
        async def handle_response(resp_payload: Any):
            if not future.done():
                future.set_result(resp_payload)

        try:
            await self.publish(event_type, payload)
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            if response_event_type in self._subscribers:
                del self._subscribers[response_event_type]

    async def publish(self, event_type: Union[EventType, str], payload: Any):
        if isinstance(payload, EventBase):
            session_id = payload.session_id or "global"
            user_id = payload.user_id or "system"
        else:
            session_id = "global"
            user_id = "system"

        event_id = getattr(payload, 'event_id', str(uuid.uuid4()))
        trace_id = f"event_{event_type}_{event_id}"
        
        trace_manager.start_trace(trace_id, session_id=session_id, user_id=user_id)
        start_time = time.time()

        subscribers = self._subscribers.get(event_type, [])
        if not subscribers:
            trace_manager.complete_trace(trace_id, metadata={"subscribers_count": 0})
            return

        tasks = []
        for subscriber in subscribers:
            tasks.append(self._run_subscriber(subscriber, event_type, payload, trace_id))

        await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = (time.time() - start_time) * 1000
        trace_manager.complete_trace(trace_id, metadata={
            "subscribers_count": len(subscribers),
            "duration_ms": duration
        })

    async def _run_subscriber(self, subscriber: SubscriberFunc, event_type: Union[EventType, str], payload: Any, parent_trace_id: str):
        sub_trace_id = f"{parent_trace_id}_{subscriber.__name__}"
        trace_manager.start_trace(sub_trace_id)
        try:
            if asyncio.iscoroutinefunction(subscriber):
                await subscriber(payload)
            else:
                subscriber(payload)
            trace_manager.complete_trace(sub_trace_id, metadata={"status": "success"})
        except Exception as e:
            logger.error(f"Error in subscriber {subscriber.__name__} for {event_type}: {e}")
            trace_manager.complete_trace(sub_trace_id, error=str(e))

class RedisEventBus(EventBus):
    """
    Redis Streams implementation for High Availability
    """
    def __init__(self, redis_url: str = "redis://localhost:6379", group_name: str = "salesboost-group", consumer_name: str = "consumer-1"):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.group_name = group_name
        self.consumer_name = consumer_name
        self._subscribers: Dict[str, List[SubscriberFunc]] = {}
        self._listening_task = None
        
    async def connect(self):
        if not self.redis:
            self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
            try:
                await self.redis.ping()
                logger.info("Connected to Redis Event Bus")
            except ConnectionError:
                logger.warning("Could not connect to Redis, functionality will be limited")

    def subscribe(self, event_type: Union[EventType, str]):
        def decorator(func: SubscriberFunc):
            key = str(event_type)
            if key not in self._subscribers:
                self._subscribers[key] = []
                # Ensure we start listening loop if not already
                if not self._listening_task:
                    self._listening_task = asyncio.create_task(self._listen_loop())
            
            if func not in self._subscribers[key]:
                self._subscribers[key].append(func)
                logger.info(f"Registered Redis subscriber {func.__name__} for {key}")
            return func
        return decorator

    async def publish(self, event_type: Union[EventType, str], payload: Any):
        if not self.redis:
            await self.connect()
            if not self.redis:
                logger.error("Redis not available, dropping event")
                return

        payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else (payload.dict() if hasattr(payload, "dict") else payload)
        if not isinstance(payload_dict, dict):
            payload_dict = {"data": payload_dict} # Wrap simple types
            
        # Serialize complex types to string for Redis
        data = {k: json.dumps(v, default=str) for k, v in payload_dict.items()}
        
        stream_key = f"stream:{event_type}"
        await self.redis.xadd(stream_key, data)
        logger.debug(f"Published to stream {stream_key}")

    async def request(self, event_type: EventType, payload: Any, timeout: float = 10.0) -> Any:
        # For Request-Response, we use a temporary list for the response
        if not self.redis:
            await self.connect()
            
        event_id = getattr(payload, 'event_id', str(uuid.uuid4()))
        response_key = f"response:{event_type}:{event_id}"
        
        # Inject response_key into payload so consumer knows where to reply
        # Note: This assumes payload is mutable or we wrap it. 
        # For simplicity in this implementation, we assume payload has a 'metadata' field or we add it to the redis message
        
        # Wait, the payload object structure is fixed by Pydantic.
        # We can add 'reply_to' in the Redis message fields, separate from payload.
        # But our publish method takes payload.
        
        # Strategy: The subscriber side for requests must be aware it needs to reply.
        # How does the subscriber know WHERE to reply?
        # Standard pattern: Message headers.
        # Redis XADD supports key-value pairs. We can add __reply_to -> response_key.
        
        # However, our `publish` method is generic.
        # Let's customize publish to support extra fields? No, keep interface simple.
        # We'll rely on convention: The subscriber logic in `bus.request` is client-side.
        # The SERVER side (consumer) needs to see "Oh, this is a request, I need to reply".
        
        # Limitation: The current implementation of consumers just runs `func(payload)`.
        # It doesn't return anything to the bus.
        # The consumer function itself must explicitly publish the response.
        # Just like in MemoryEventBus test: `await test_bus.publish(response_topic, "pong")`.
        
        # So, we just need to subscribe to the response channel/list.
        # Using BLPOP on a list is better for one-time response.
        
        await self.publish(event_type, payload)
        
        try:
            # Wait for response on the list
            # blpop returns (key, element)
            result = await asyncio.wait_for(self.redis.blpop(response_key, timeout=timeout), timeout=timeout)
            if result:
                return json.loads(result[1])
            return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for response to {event_type} {event_id}")
            raise
        finally:
            await self.redis.delete(response_key)

    async def _listen_loop(self):
        # Simplistic implementation: Polling streams or using XREADGROUP
        # For this prototype, we'll iterate over subscribed topics.
        # In prod, use XREADGROUP.
        if not self.redis:
            await self.connect()

        while True:
            if not self._subscribers:
                await asyncio.sleep(1)
                continue
                
            {f"stream:{k}": "$" for k in self._subscribers.keys()}
            # First time, use $ to get new messages.
            # We need to maintain last_id for each stream if not using groups.
            # To support "Cloud Native" with persistence, Groups are best.
            
            # Setup groups if not exist
            for key in self._subscribers.keys():
                stream_key = f"stream:{key}"
                try:
                    await self.redis.xgroup_create(stream_key, self.group_name, mkstream=True)
                except Exception:
                    pass # Group likely exists

            try:
                # Read from group
                streams_args = {f"stream:{k}": ">" for k in self._subscribers.keys()}
                events = await self.redis.xreadgroup(self.group_name, self.consumer_name, streams_args, count=10, block=1000)
                
                for stream_key, messages in events:
                    event_type = stream_key.replace("stream:", "")
                    for message_id, data in messages:
                        # Process message
                        # data is dict of strings.
                        # Reconstruct payload. We need to know the Type.
                        # For now, return the dict.
                        
                        # In a real app, we'd deserialize back to Pydantic based on EventType registry.
                        # Here we pass the dict to the subscriber.
                        
                        # Decode json values
                        decoded_data = {}
                        for k, v in data.items():
                            try:
                                decoded_data[k] = json.loads(v)
                            except:
                                decoded_data[k] = v

                        subscribers = self._subscribers.get(event_type, [])
                        for sub in subscribers:
                            try:
                                # We assume subscriber handles dict or we need to cast it?
                                # Ideally we cast it. But we don't have the class ref here easily.
                                # Passing dict for now.
                                if asyncio.iscoroutinefunction(sub):
                                    await sub(decoded_data)
                                else:
                                    sub(decoded_data)
                            except Exception as e:
                                logger.error(f"Subscriber failed: {e}")
                        
                        # Ack
                        await self.redis.xack(stream_key, self.group_name, message_id)
            
                # Periodically claim pending messages (PEL) - every 10 iterations (approx 10s)
                # In production, this might be a separate background task
                if int(time.time()) % 10 == 0:
                    await self._recover_pending()
                        
            except Exception as e:
                logger.error(f"Error in Redis loop: {e}")
                await asyncio.sleep(1)

    async def _recover_pending(self):
        """
        Recover pending messages (PEL) that were not acknowledged.
        Uses XAUTOCLAIM to transfer ownership to this consumer and retry.
        """
        if not self.redis: return
        
        for key in self._subscribers.keys():
            stream_key = f"stream:{key}"
            try:
                # XAUTOCLAIM: key, group, consumer, min_idle_time_ms, start_id, count
                # 60000ms = 1 minute timeout for pending messages
                messages = await self.redis.xautoclaim(stream_key, self.group_name, self.consumer_name, 60000, "0-0", count=5)
                # messages is [next_id, [ (id, fields), ... ]]
                if messages and len(messages) > 1 and messages[1]:
                    logger.info(f"Claimed {len(messages[1])} pending messages for {key}")
                    for message_id, data in messages[1]:
                         # Process claimed message (Reuse processing logic? For now, simplified inline)
                         # In real impl, refactor processing to _process_message(event_type, data)
                         pass # Pending messages are now owned by us, will be processed in next read? 
                         # No, xautoclaim returns them, we must process them NOW.
                         
                         event_type = key
                         # Decode
                         decoded_data = {}
                         for k, v in data.items():
                            try:
                                decoded_data[k] = json.loads(v)
                            except:
                                decoded_data[k] = v
                                
                         subscribers = self._subscribers.get(event_type, [])
                         for sub in subscribers:
                            try:
                                if asyncio.iscoroutinefunction(sub):
                                    await sub(decoded_data)
                                else:
                                    sub(decoded_data)
                            except Exception as e:
                                logger.error(f"Subscriber failed during recovery: {e}")
                         
                         await self.redis.xack(stream_key, self.group_name, message_id)

            except Exception as e:
                logger.warning(f"Error recovering pending messages for {stream_key}: {e}")

# Factory to choose implementation
# Default to Memory for now to avoid breaking existing tests without Redis
# In production, this would read env var.
USE_REDIS = os.getenv("USE_REDIS_BUS", "false").lower() == "true"

if USE_REDIS:
    bus = RedisEventBus()
else:
    bus = MemoryEventBus()
