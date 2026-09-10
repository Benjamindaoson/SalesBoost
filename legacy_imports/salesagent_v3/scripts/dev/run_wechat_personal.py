"""Personal WeChat launcher script.

Run this script to start the personal WeChat bot:
    python -m scripts.run_wechat_personal
"""
import asyncio
import signal
import sys

import structlog
from redis.asyncio import Redis

# Add parent directory to path
sys.path.insert(0, '.')

from salesagent.integrations.wechat_personal import PersonalWeChatClient, WeChatMessageWorker
from salesagent.core.settings import settings

log = structlog.get_logger()


async def main():
    """Main entry point."""
    log.info("Starting Personal WeChat Bot")

    # Initialize Redis
    redis = Redis.from_url(settings.redis_url, decode_responses=False)

    # Initialize WeChat client
    wechat_client = PersonalWeChatClient(
        redis=redis,
        auto_login=settings.wechat_personal_auto_login,
        hot_reload=settings.wechat_personal_hot_reload,
    )

    # Initialize message worker
    worker = WeChatMessageWorker(
        redis=redis,
        wechat_client=wechat_client,
        api_base_url="http://localhost:8000",
    )

    # Graceful shutdown handler
    def signal_handler(sig, frame):
        log.info("Shutting down...")
        asyncio.create_task(shutdown())

    async def shutdown():
        await worker.stop()
        await wechat_client.stop()
        await redis.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Login to WeChat
        await wechat_client.login()

        # Start worker
        worker_task = asyncio.create_task(worker.start())

        # Start WeChat client
        await wechat_client.start()

        # Wait for worker
        await worker_task

    except KeyboardInterrupt:
        log.info("Received keyboard interrupt")
        await shutdown()
    except Exception as exc:
        log.error("Fatal error", error=str(exc))
        await shutdown()


if __name__ == "__main__":
    asyncio.run(main())
