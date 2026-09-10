"""Adaptive Prompt Optimization Engine."""
from __future__ import annotations

import json
from typing import Any

import structlog

log = structlog.get_logger()

# Min number of evaluations before APO considers a prompt underperforming
MIN_EVALUATIONS = 10
UNDERPERFORM_THRESHOLD = 0.60


class APOEngine:
    """
    Adaptive Prompt Optimization Engine.

    Cycle (every N conversations):
    1. Find prompt versions with avg_reward < threshold
    2. Use LLM to generate N variant templates
    3. Register variants in PromptRegistry at low traffic weight
    4. Over time, A/B test determines which variant wins
    """

    def __init__(self, db: Any, gateway: Any) -> None:
        self.db = db
        self.gateway = gateway

    async def run_cycle(self) -> dict[str, Any]:
        from sqlalchemy import select
        from salesagent.models.db_models import PromptTemplate

        result = await self.db.execute(
            select(PromptTemplate).where(
                PromptTemplate.status == "active",
                PromptTemplate.avg_reward < UNDERPERFORM_THRESHOLD,
                PromptTemplate.avg_reward > 0,
            )
        )
        underperforming = result.scalars().all()

        generated = []
        for prompt in underperforming:
            variants = await self._generate_variants(prompt)
            for v in variants:
                new_prompt = PromptTemplate(
                    name=prompt.name,
                    version=prompt.version + 100,  # shadow version
                    template=v,
                    variables=prompt.variables,
                    description=f"APO variant of v{prompt.version}",
                    status="shadow",
                    traffic_weight=0.10,
                )
                self.db.add(new_prompt)
                generated.append({"name": prompt.name, "variant_count": len(variants)})

        await self.db.commit()
        return {"cycles_run": len(underperforming), "variants_generated": generated}

    async def _generate_variants(self, prompt: Any) -> list[str]:
        from salesagent.core.settings import settings
        from salesagent.reasoning.prompts import APO_VARIANT_PROMPT

        prompt_text = APO_VARIANT_PROMPT.format(
            avg_reward=prompt.avg_reward,
            target_reward=0.75,
            current_prompt=prompt.template[:1000],
            n_variants=settings.apo_variant_count,
        )
        try:
            raw = await self.gateway.complete(
                task="apo_variant",
                system="You are a prompt engineering expert.",
                user=prompt_text,
            )
            variants = json.loads(raw)
            return variants[:settings.apo_variant_count] if isinstance(variants, list) else []
        except Exception:
            return []
