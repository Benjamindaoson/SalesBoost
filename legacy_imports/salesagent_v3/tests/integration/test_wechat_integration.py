"""WeChat integration test script.

Tests both personal WeChat and enterprise WeChat integrations.
"""
import asyncio
import sys

sys.path.insert(0, '.')

from redis.asyncio import Redis
from salesagent.integrations.wechat_personal import PersonalWeChatClient
from salesagent.integrations.wechat_work import WeChatWorkClient
from salesagent.core.settings import settings


async def test_personal_wechat():
    """Test personal WeChat integration."""
    print("\n=== Testing Personal WeChat ===")

    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    client = PersonalWeChatClient(redis=redis, auto_login=False)

    try:
        await client.initialize()
        print("✓ Personal WeChat client initialized")

        # Note: Actual login requires QR code scan
        print("⚠ Login requires QR code scan (skipped in test)")

        # Test would continue with:
        # await client.login()
        # friends = client.get_friends()
        # print(f"✓ Found {len(friends)} friends")

    except ImportError:
        print("✗ itchat not installed. Run: pip install itchat")
    except Exception as exc:
        print(f"✗ Error: {exc}")
    finally:
        await redis.close()


async def test_wechat_work():
    """Test enterprise WeChat integration."""
    print("\n=== Testing WeChat Work ===")

    if not settings.wechat_work_corp_id:
        print("⚠ WeChat Work not configured (missing WECHAT_WORK_CORP_ID)")
        return

    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    client = WeChatWorkClient(redis=redis)

    try:
        # Test access token
        token = await client.get_access_token()
        print(f"✓ Access token obtained: {token[:20]}...")

        # Test signature verification
        is_valid = client.verify_signature(
            signature="test_signature",
            timestamp="1234567890",
            nonce="test_nonce",
        )
        print(f"✓ Signature verification: {is_valid}")

    except Exception as exc:
        print(f"✗ Error: {exc}")
    finally:
        await redis.close()


async def main():
    """Run all tests."""
    print("WeChat Integration Test Suite")
    print("=" * 50)

    await test_personal_wechat()
    await test_wechat_work()

    print("\n" + "=" * 50)
    print("Test suite completed")


if __name__ == "__main__":
    asyncio.run(main())
