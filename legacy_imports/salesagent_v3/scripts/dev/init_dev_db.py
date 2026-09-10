"""Create development database tables from the current SQLAlchemy models."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from salesagent.dependencies import _engine
from salesagent.models.db_models import Base


async def main() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(main())
