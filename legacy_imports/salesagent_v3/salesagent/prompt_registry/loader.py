"""Prompt Registry Loader."""
from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from salesagent.main import AsyncSessionLocal

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()


class PromptLoader:
    """Loads exact versions of prompts into memory at startup or periodically."""

    @classmethod
    async def get_active_prompts(cls) -> dict[str, str]:
        """Fetch all active prompt templates."""
        from sqlalchemy import select
        from salesagent.models.db_models import PromptTemplate

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(PromptTemplate).where(PromptTemplate.status == "active")
            )
            prompts = result.scalars().all()
            return {p.name: p.template for p in prompts}

    @classmethod
    async def get_prompt_versions(cls, name: str) -> list[dict[str, any]]:
        """Get all versions of a specific prompt."""
        from sqlalchemy import select
        from salesagent.models.db_models import PromptTemplate

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(PromptTemplate)
                .where(PromptTemplate.name == name)
                .order_by(PromptTemplate.version.desc())
            )
            prompts = result.scalars().all()
            return [
                {
                    "id": p.id,
                    "version": p.version,
                    "status": p.status,
                    "traffic_weight": p.traffic_weight,
                    "avg_reward": p.avg_reward,
                    "created_at": p.created_at,
                }
                for p in prompts
            ]

    @classmethod
    async def rollback_prompt(cls, name: str, target_version: int) -> dict[str, any]:
        """
        Rollback a prompt to a specific version.

        Steps:
        1. Set all versions of this prompt to 'archived'
        2. Set the target version to 'active' with traffic_weight=1.0
        3. Return the activated prompt details
        """
        from sqlalchemy import select, update
        from salesagent.models.db_models import PromptTemplate

        async with AsyncSessionLocal() as db:
            async with db.begin():
                # Archive all versions
                await db.execute(
                    update(PromptTemplate)
                    .where(PromptTemplate.name == name)
                    .values(status="archived", traffic_weight=0.0)
                )

                # Activate target version
                await db.execute(
                    update(PromptTemplate)
                    .where(
                        PromptTemplate.name == name,
                        PromptTemplate.version == target_version,
                    )
                    .values(status="active", traffic_weight=1.0)
                )

            # Fetch the activated prompt
            result = await db.execute(
                select(PromptTemplate).where(
                    PromptTemplate.name == name,
                    PromptTemplate.version == target_version,
                )
            )
            prompt = result.scalar_one_or_none()

            if not prompt:
                raise ValueError(f"Prompt {name} version {target_version} not found")

            log.info(
                "Prompt rolled back",
                name=name,
                target_version=target_version,
                prompt_id=prompt.id,
            )

            return {
                "id": prompt.id,
                "name": prompt.name,
                "version": prompt.version,
                "status": prompt.status,
                "traffic_weight": prompt.traffic_weight,
            }

    @classmethod
    async def load_defaults_if_empty(cls) -> None:
        """Seed the DB with the hardcoded prompts if the registry is empty."""
        from sqlalchemy import func, select
        from salesagent.models.db_models import PromptTemplate
        from salesagent.reasoning.prompts import (
            APO_VARIANT_PROMPT,
            CRITIC_SCORING_PROMPT,
            EVOLUTION_REVIEW_PROMPT,
            GUARD_REWRITE_PROMPT,
            REASONING_SYSTEM_PROMPT,
            RESPONSE_SYSTEM_PROMPT,
            SELFRAG_FILTER_PROMPT,
            SYNTHETIC_DIALOGUE_PROMPT,
        )

        defaults = {
            "reasoning_system": REASONING_SYSTEM_PROMPT,
            "response_system": RESPONSE_SYSTEM_PROMPT,
            "critic_scoring": CRITIC_SCORING_PROMPT,
            "guard_rewrite": GUARD_REWRITE_PROMPT,
            "selfrag_filter": SELFRAG_FILTER_PROMPT,
            "synthetic_dialogue": SYNTHETIC_DIALOGUE_PROMPT,
            "evolution_review": EVOLUTION_REVIEW_PROMPT,
            "apo_variant": APO_VARIANT_PROMPT,
        }

        async with AsyncSessionLocal() as db:
            count = await db.scalar(select(func.count(PromptTemplate.id)))
            if count == 0:
                for name, template in defaults.items():
                    prompt = PromptTemplate(
                        name=name,
                        version=1,
                        template=template,
                        status="active",
                        traffic_weight=1.0,
                    )
                    db.add(prompt)
                await db.commit()
                log.info("PromptRegistry: seeded defaults")
