"""Synthetic Data Engine — generates training dialogues for cold start."""
from __future__ import annotations

import json
from typing import Any

import structlog

from salesagent.core.constants import SaleStage

log = structlog.get_logger()


class SyntheticDataGenerator:
    """
    Generates realistic B2B sales dialogues using a strong LLM (e.g. Claude 3.5 Sonnet)
    by combining persona, sales stage, and objection type into a Cartesian product matrix.
    Useful for cold-starting the Reward Model and DPO dataset.
    """

    def __init__(self, gateway: Any) -> None:
        self.gateway = gateway

    async def generate_dialogue(
        self,
        persona: str,
        stage: SaleStage,
        objection_type: str,
        num_turns: int = 5,
    ) -> list[dict[str, str]]:
        from salesagent.reasoning.prompts import SYNTHETIC_DIALOGUE_PROMPT

        prompt = SYNTHETIC_DIALOGUE_PROMPT.format(
            persona=persona,
            stage=stage.value,
            objection_type=objection_type,
            num_turns=num_turns,
        )

        try:
            raw = await self.gateway.complete(
                task="synthetic",
                system="You are an expert at writing realistic B2B sales roleplays.",
                user=prompt,
                response_format="json_object",
            )
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "dialogue" in data:
                return data["dialogue"]
            return []
        except Exception as exc:
            log.warning("Synthetic generation failed", error=str(exc))
            return []

    async def generate_batch(self, count: int) -> list[list[dict[str, str]]]:
        """Generate a diverse batch of dialogues (mock implementation for demo)."""
        import asyncio
        from salesagent.core.settings import settings

        if settings.mock_llm:
            return [
                [
                    {"role": "user", "content": "你们的价格比A公司贵了30%"},
                    {"role": "assistant", "content": "我完全理解您对预算的考量。很多客户最初也有同样的顾虑。不过如果算上我们方案提升的效率，实际上ROI是更高的。能分享下您目前团队在这一块投入的人力成本吗？"}
                ]
            ] * count

        # In production: cartesian product of personas X stages X objections
        tasks = [
            self.generate_dialogue(
                persona="CTO, cost-sensitive",
                stage=SaleStage.OBJECTION,
                objection_type="price_sensitivity",
            )
            for _ in range(count)
        ]
        return await asyncio.gather(*tasks)
