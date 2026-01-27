import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agents.ask.coach_agent import SalesCoachAgent
from app.observability.metrics.alerting import alert_manager
from core.exceptions import AgentError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_coach_agent():
    logger.info("Testing SalesCoachAgent...")
    agent = SalesCoachAgent()
    try:
        advice = await agent.get_advice(
            history=[{"role": "user", "content": "Hello"}],
            session_id="test_session"
        )
        logger.info(f"Success! Advice: {advice.action_advice}")
    except Exception as e:
        logger.error(f"Failed: {e}")

async def test_alerting():
    logger.info("Testing AlertManager...")
    metrics = {"sentiment_score": 0.1, "refusal_rate": 0.2}
    await alert_manager.check_business_metrics(metrics)
    logger.info("Alert checks completed (check logs for warnings).")

async def main():
    await test_coach_agent()
    await test_alerting()

if __name__ == "__main__":
    asyncio.run(main())
