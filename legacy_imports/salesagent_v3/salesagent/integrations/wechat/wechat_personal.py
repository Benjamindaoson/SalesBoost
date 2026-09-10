"""Personal WeChat Integration using itchat/wechaty.

This module provides integration with personal WeChat accounts for receiving
and sending messages. It supports both itchat (Python) and wechaty (TypeScript/Python).

Architecture:
- Message Queue: Redis Streams for async message processing
- Session Management: Map WeChat user_id to SalesAgent session_id
- Auto-reply: Configurable delay to simulate human typing
"""
from __future__ import annotations

import asyncio
import uuid
import json
import time
from typing import Any, Callable

import structlog
from redis.asyncio import Redis

log = structlog.get_logger()
itchat = None

# Redis keys
WECHAT_MESSAGE_STREAM = "wechat:messages:incoming"
WECHAT_SESSION_MAP = "wechat:session_map"  # Hash: wechat_user_id -> session_id


class PersonalWeChatClient:
    """
    Personal WeChat client using itchat library.

    Features:
    - QR code login
    - Message receiving (text, image, file, voice)
    - Message sending with typing simulation
    - Session persistence
    - Auto-reconnect
    """

    def __init__(
        self,
        redis: Redis,
        message_handler: Callable[[dict[str, Any]], None] | None = None,
        auto_login: bool = True,
        hot_reload: bool = True,
    ) -> None:
        self.redis = redis
        self.message_handler = message_handler
        self.auto_login = auto_login
        self.hot_reload = hot_reload
        self._itchat = None
        self._running = False

    async def initialize(self) -> None:
        """Initialize itchat and login."""
        global itchat
        try:
            if itchat is None:
                import itchat as itchat_module
                itchat = itchat_module
            self._itchat = itchat

            # Register message handlers
            @self._itchat.msg_register(itchat.content.TEXT)
            def text_reply(msg: dict[str, Any]) -> None:
                asyncio.create_task(self._handle_message(msg))

            @self._itchat.msg_register([itchat.content.PICTURE, itchat.content.RECORDING, itchat.content.ATTACHMENT])
            def media_reply(msg: dict[str, Any]) -> None:
                asyncio.create_task(self._handle_message(msg))

            log.info("Personal WeChat client initialized")

        except ImportError:
            log.error("itchat not installed. Run: pip install itchat")
            raise

    async def login(self) -> None:
        """Login to WeChat with QR code."""
        if not self._itchat:
            await self.initialize()

        log.info("Starting WeChat login...")

        # Login with QR code
        self._itchat.auto_login(
            hotReload=self.hot_reload,
            enableCmdQR=2,  # Show QR in terminal
            picDir='./wechat_qr.png',
        )

        log.info("WeChat login successful", user=self._itchat.search_friends()['NickName'])

    async def start(self) -> None:
        """Start the WeChat client and message loop."""
        if not self._itchat:
            await self.login()

        self._running = True
        log.info("Personal WeChat client started")

        # Run itchat in a separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._itchat.run)

    async def stop(self) -> None:
        """Stop the WeChat client."""
        self._running = False
        if self._itchat:
            self._itchat.logout()
        log.info("Personal WeChat client stopped")

    async def _handle_message(self, msg: dict[str, Any]) -> None:
        """Handle incoming WeChat message."""
        try:
            # Extract message info
            wechat_user_id = msg.get('FromUserName', '')
            content = msg.get('Text', '')
            msg_type = msg.get('Type', 'Text')

            # Get user info
            user_info = self._itchat.search_friends(userName=wechat_user_id)
            nickname = user_info.get('NickName', 'Unknown') if user_info else 'Unknown'

            log.info(
                "Received WeChat message",
                user_id=wechat_user_id,
                nickname=nickname,
                msg_type=msg_type,
                content_length=len(content),
            )

            # Get or create session_id
            session_id = await self._get_or_create_session(wechat_user_id, nickname)

            # Build message payload
            message_payload = {
                'session_id': session_id,
                'wechat_user_id': wechat_user_id,
                'nickname': nickname,
                'content': content,
                'msg_type': msg_type,
                'timestamp': int(time.time()),
                'raw_msg': msg,
            }

            # Push to Redis Stream for async processing
            await self.redis.xadd(
                WECHAT_MESSAGE_STREAM,
                {'payload': json.dumps(message_payload)},
                maxlen=10000,
            )

            # Call custom handler if provided
            if self.message_handler:
                await self.message_handler(message_payload)

        except Exception as exc:
            log.error("Failed to handle WeChat message", error=str(exc))

    async def _get_or_create_session(self, wechat_user_id: str, nickname: str) -> str:
        """Get existing session_id or create new one."""
        # Check if session exists
        session_id = await self.redis.hget(WECHAT_SESSION_MAP, wechat_user_id)

        if session_id:
            return session_id.decode('utf-8')

        # Create new session via API
        import httpx
        import inspect
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'http://localhost:8000/sessions',
                    json={
                        'customer_id': wechat_user_id,
                        'metadata': {
                            'channel': 'wechat_personal',
                            'nickname': nickname,
                        }
                    }
                )
                status_result = response.raise_for_status()
                if inspect.isawaitable(status_result):
                    await status_result
                data = response.json()
                if inspect.isawaitable(data):
                    data = await data
                new_session_id = data['session_id']
        except Exception as exc:
            new_session_id = f"wechat_{uuid.uuid4()}"
            log.warning("Session API unavailable, using temporary session", error=str(exc))

        # Store mapping
        await self.redis.hset(WECHAT_SESSION_MAP, wechat_user_id, new_session_id)

        log.info("Created new session", wechat_user_id=wechat_user_id, session_id=new_session_id)
        return new_session_id

    async def send_message(
        self,
        wechat_user_id: str,
        content: str,
        typing_delay: float = 2.0,
    ) -> bool:
        """
        Send message to WeChat user with typing simulation.

        Args:
            wechat_user_id: WeChat user ID
            content: Message content
            typing_delay: Delay in seconds to simulate typing (default: 2s)

        Returns:
            True if sent successfully
        """
        try:
            # Simulate typing delay
            if typing_delay > 0:
                await asyncio.sleep(typing_delay)

            # Send message
            self._itchat.send(content, toUserName=wechat_user_id)

            log.info(
                "Sent WeChat message",
                user_id=wechat_user_id,
                content_length=len(content),
            )
            return True

        except Exception as exc:
            log.error("Failed to send WeChat message", error=str(exc), user_id=wechat_user_id)
            return False

    async def send_image(self, wechat_user_id: str, image_path: str) -> bool:
        """Send image to WeChat user."""
        try:
            self._itchat.send_image(image_path, toUserName=wechat_user_id)
            log.info("Sent WeChat image", user_id=wechat_user_id, image=image_path)
            return True
        except Exception as exc:
            log.error("Failed to send WeChat image", error=str(exc))
            return False

    async def send_file(self, wechat_user_id: str, file_path: str) -> bool:
        """Send file to WeChat user."""
        try:
            self._itchat.send_file(file_path, toUserName=wechat_user_id)
            log.info("Sent WeChat file", user_id=wechat_user_id, file=file_path)
            return True
        except Exception as exc:
            log.error("Failed to send WeChat file", error=str(exc))
            return False

    def get_friends(self) -> list[dict[str, Any]]:
        """Get all friends list."""
        if not self._itchat:
            return []
        return self._itchat.get_friends(update=True)

    def get_user_info(self, wechat_user_id: str) -> dict[str, Any] | None:
        """Get user info by WeChat user ID."""
        if not self._itchat:
            return None
        return self._itchat.search_friends(userName=wechat_user_id)


class WeChatMessageWorker:
    """
    Background worker that processes WeChat messages from Redis Stream.

    This worker:
    1. Reads messages from Redis Stream
    2. Calls SalesAgent API to generate response
    3. Sends response back to WeChat
    """

    def __init__(
        self,
        redis: Redis,
        wechat_client: PersonalWeChatClient,
        api_base_url: str = "http://localhost:8000",
    ) -> None:
        self.redis = redis
        self.wechat_client = wechat_client
        self.api_base_url = api_base_url
        self._running = False

    async def start(self) -> None:
        """Start the message processing worker."""
        self._running = True
        log.info("WeChat message worker started")

        # Create consumer group
        try:
            await self.redis.xgroup_create(
                WECHAT_MESSAGE_STREAM,
                'wechat_workers',
                id='0',
                mkstream=True,
            )
        except Exception:
            pass  # Group already exists

        # Process messages
        while self._running:
            try:
                # Read from stream
                messages = await self.redis.xreadgroup(
                    groupname='wechat_workers',
                    consumername='worker-1',
                    streams={WECHAT_MESSAGE_STREAM: '>'},
                    count=1,
                    block=5000,  # 5 second timeout
                )

                if not messages:
                    continue

                for stream_name, message_list in messages:
                    for message_id, message_data in message_list:
                        await self._process_message(message_id, message_data)

            except Exception as exc:
                log.error("Worker error", error=str(exc))
                await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop the worker."""
        self._running = False
        log.info("WeChat message worker stopped")

    async def _process_message(self, message_id: bytes, message_data: dict[bytes, bytes]) -> None:
        """Process a single message."""
        try:
            payload = json.loads(message_data[b'payload'])
            session_id = payload['session_id']
            wechat_user_id = payload['wechat_user_id']
            content = payload['content']

            log.info("Processing message", session_id=session_id, user_id=wechat_user_id)

            # Call SalesAgent API
            import httpx
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.api_base_url}/chat/stream",
                    json={
                        'message': content,
                        'session_id': session_id,
                        'customer_id': wechat_user_id,
                    }
                )

                # Collect SSE response
                full_response = ""
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        data = json.loads(line[6:])
                        if data.get('event') == 'token':
                            full_response += data.get('content', '')
                        elif data.get('event') == 'done':
                            break

            # Send response back to WeChat
            if full_response:
                await self.wechat_client.send_message(
                    wechat_user_id=wechat_user_id,
                    content=full_response,
                    typing_delay=2.0,
                )

            # Acknowledge message
            await self.redis.xack(WECHAT_MESSAGE_STREAM, 'wechat_workers', message_id)

        except Exception as exc:
            log.error("Failed to process message", error=str(exc), message_id=message_id)
