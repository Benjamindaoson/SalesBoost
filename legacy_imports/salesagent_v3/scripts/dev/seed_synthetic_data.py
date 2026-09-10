import asyncio
import sys
import os
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from salesagent.main import AsyncSessionLocal
from salesagent.flywheel.synthetic_data import SyntheticDataGenerator
from salesagent.llm.gateway import ModelGateway

async def main():
    print(f"[{datetime.now()}] Starting synthetic data seeding...")
    gateway = ModelGateway()
    await gateway.initialize()

    generator = SyntheticDataGenerator(gateway=gateway)
    batch = await generator.generate_batch(count=5)

    print(f"Generated {len(batch)} mock dialogues. Seeding complete.")

if __name__ == "__main__":
    asyncio.run(main())
