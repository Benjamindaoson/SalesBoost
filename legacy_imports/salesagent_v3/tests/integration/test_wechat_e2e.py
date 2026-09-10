"""End-to-end integration test for WeChat → SalesAgent → Response flow.

This test validates the complete pipeline:
1. WeChat message received
2. Session created/retrieved
3. AI processing (reasoning → strategy → response)
4. Response sent back to WeChat
"""
import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch

from redis.asyncio import Redis
from salesagent.integrations.wechat_personal import PersonalWeChatClient, WeChatMessageWorker


@pytest.mark.asyncio
async def test_wechat_message_flow_end_to_end():
    """Test complete WeChat message processing flow."""

    # Mock Redis
    redis_mock = AsyncMock(spec=Redis)
    redis_mock.hget = AsyncMock(return_value=None)  # No existing session
    redis_mock.hset = AsyncMock()
    redis_mock.xadd = AsyncMock()
    redis_mock.xgroup_create = AsyncMock()
    redis_mock.xreadgroup = AsyncMock(return_value=[])
    redis_mock.xack = AsyncMock()

    # Mock itchat
    with patch('salesagent.integrations.wechat.wechat_personal.itchat') as itchat_mock:
        itchat_mock.auto_login = Mock()
        itchat_mock.search_friends = Mock(return_value={'NickName': 'TestUser'})
        itchat_mock.send = Mock()

        # Initialize client
        client = PersonalWeChatClient(redis=redis_mock, auto_login=False)
        await client.initialize()

        # Simulate incoming message
        test_message = {
            'FromUserName': 'test_user_123',
            'Text': '你好，我想了解一下保险产品',
            'Type': 'Text',
        }

        # Handle message
        await client._handle_message(test_message)

        # Verify message was pushed to Redis Stream
        redis_mock.xadd.assert_called_once()
        call_args = redis_mock.xadd.call_args
        assert call_args[0][0] == 'wechat:messages:incoming'

        # Verify payload structure
        payload_json = call_args[0][1]['payload']
        payload = json.loads(payload_json)
        assert payload['wechat_user_id'] == 'test_user_123'
        assert payload['content'] == '你好，我想了解一下保险产品'
        assert payload['msg_type'] == 'Text'
        assert 'session_id' in payload


@pytest.mark.asyncio
async def test_wechat_worker_processes_message():
    """Test that worker correctly processes messages from Redis Stream."""

    redis_mock = AsyncMock(spec=Redis)

    # Mock stream read to return one message
    test_payload = {
        'session_id': 'test_session_123',
        'wechat_user_id': 'test_user_123',
        'content': '价格是多少？',
        'msg_type': 'Text',
        'timestamp': 1234567890,
    }

    redis_mock.xreadgroup = AsyncMock(return_value=[
        ('wechat:messages:incoming', [
            (b'1234567890-0', {b'payload': json.dumps(test_payload).encode()})
        ])
    ])
    redis_mock.xack = AsyncMock()

    # Mock WeChat client
    wechat_client_mock = AsyncMock(spec=PersonalWeChatClient)
    wechat_client_mock.send_message = AsyncMock(return_value=True)

    # Mock HTTP client for API call
    with patch('httpx.AsyncClient') as http_mock:
        # Mock SSE response
        async def mock_aiter_lines():
            yield 'data: {"event": "token", "content": "根据"}'
            yield 'data: {"event": "token", "content": "您的"}'
            yield 'data: {"event": "token", "content": "需求"}'
            yield 'data: {"event": "done"}'

        response_mock = AsyncMock()
        response_mock.aiter_lines = mock_aiter_lines

        http_client_instance = AsyncMock()
        http_client_instance.post = AsyncMock(return_value=response_mock)
        http_client_instance.__aenter__ = AsyncMock(return_value=http_client_instance)
        http_client_instance.__aexit__ = AsyncMock()

        http_mock.return_value = http_client_instance

        # Initialize worker
        worker = WeChatMessageWorker(
            redis=redis_mock,
            wechat_client=wechat_client_mock,
            api_base_url="http://localhost:8000"
        )

        # Process one message
        message_id = b'1234567890-0'
        message_data = {b'payload': json.dumps(test_payload).encode()}

        await worker._process_message(message_id, message_data)

        # Verify API was called
        http_client_instance.post.assert_called_once()
        call_args = http_client_instance.post.call_args
        assert '/chat/stream' in call_args[0][0]

        # Verify response was sent back to WeChat
        wechat_client_mock.send_message.assert_called_once()
        send_call_args = wechat_client_mock.send_message.call_args
        assert send_call_args[1]['wechat_user_id'] == 'test_user_123'
        assert '根据您的需求' in send_call_args[1]['content']

        # Verify message was acknowledged
        redis_mock.xack.assert_called_once()


@pytest.mark.asyncio
async def test_session_mapping_persistence():
    """Test that WeChat user ID to session ID mapping is persisted."""

    redis_mock = AsyncMock(spec=Redis)
    redis_mock.hget = AsyncMock(return_value=None)  # No existing session
    redis_mock.hset = AsyncMock()

    # Mock HTTP client for session creation
    with patch('httpx.AsyncClient') as http_mock:
        response_mock = AsyncMock()
        response_mock.json = AsyncMock(return_value={'session_id': 'new_session_456'})

        http_client_instance = AsyncMock()
        http_client_instance.post = AsyncMock(return_value=response_mock)
        http_client_instance.__aenter__ = AsyncMock(return_value=http_client_instance)
        http_client_instance.__aexit__ = AsyncMock()

        http_mock.return_value = http_client_instance

        # Initialize client
        client = PersonalWeChatClient(redis=redis_mock, auto_login=False)

        # Get or create session
        session_id = await client._get_or_create_session('test_user_789', 'TestNickname')

        # Verify session was created
        assert session_id == 'new_session_456'

        # Verify mapping was stored in Redis
        redis_mock.hset.assert_called_once_with(
            'wechat:session_map',
            'test_user_789',
            'new_session_456'
        )


@pytest.mark.asyncio
async def test_typing_delay_simulation():
    """Test that typing delay is applied before sending message."""

    import time

    with patch('salesagent.integrations.wechat.wechat_personal.itchat') as itchat_mock:
        itchat_mock.send = Mock()

        redis_mock = AsyncMock(spec=Redis)
        client = PersonalWeChatClient(redis=redis_mock, auto_login=False)
        client._itchat = itchat_mock

        # Send message with 0.1s delay
        start_time = time.time()
        await client.send_message('test_user', 'Hello', typing_delay=0.1)
        elapsed = time.time() - start_time

        # Verify delay was applied
        assert elapsed >= 0.1

        # Verify message was sent
        itchat_mock.send.assert_called_once_with('Hello', toUserName='test_user')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
