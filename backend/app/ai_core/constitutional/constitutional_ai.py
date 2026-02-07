"""
Constitutional AI 2.0 - 价值对齐系统

2026年前沿算法：Constitutional AI with Self-Critique

核心思想：
1. 定义销售伦理宪法（Constitution）
2. 自我批评和修正（Self-Critique）
3. 多轮迭代优化
4. 价值对齐保证

Author: Claude (Anthropic)
Version: 2026.1
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PrincipleCategory(str, Enum):
    """原则类别"""
    HONESTY = "honesty"
    RESPECT = "respect"
    ACCURACY = "accuracy"
    EMPATHY = "empathy"
    COMPLIANCE = "compliance"


@dataclass
class Principle:
    """伦理原则"""
    category: PrincipleCategory
    statement: str
    critique_prompt: str
    weight: float = 1.0


@dataclass
class Critique:
    """批评结果"""
    principle: Principle
    aligned: bool
    confidence: float
    reason: str
    suggested_revision: Optional[str] = None


@dataclass
class Constitution:
    """销售伦理宪法"""
    principles: List[Principle] = field(default_factory=list)

    @classmethod
    def create_sales_constitution(cls) -> Constitution:
        """创建销售伦理宪法"""
        principles = [
            # Honesty principles
            Principle(
                category=PrincipleCategory.HONESTY,
                statement="Never mislead customers about product capabilities",
                critique_prompt="Does this response mislead the customer about what the product can do?",
                weight=1.5
            ),
            Principle(
                category=PrincipleCategory.HONESTY,
                statement="Always disclose limitations and constraints",
                critique_prompt="Does this response hide important limitations or constraints?",
                weight=1.3
            ),

            # Respect principles
            Principle(
                category=PrincipleCategory.RESPECT,
                statement="Respect customer autonomy and decision-making",
                critique_prompt="Does this response pressure or manipulate the customer?",
                weight=1.4
            ),
            Principle(
                category=PrincipleCategory.RESPECT,
                statement="Honor customer's time and boundaries",
                critique_prompt="Does this response respect the customer's time and boundaries?",
                weight=1.0
            ),

            # Accuracy principles
            Principle(
                category=PrincipleCategory.ACCURACY,
                statement="Provide accurate product information",
                critique_prompt="Is all product information in this response accurate?",
                weight=1.5
            ),
            Principle(
                category=PrincipleCategory.ACCURACY,
                statement="Use verified data and avoid speculation",
                critique_prompt="Does this response speculate or use unverified information?",
                weight=1.2
            ),

            # Empathy principles
            Principle(
                category=PrincipleCategory.EMPATHY,
                statement="Handle objections empathetically",
                critique_prompt="Does this response show empathy for customer concerns?",
                weight=1.1
            ),
            Principle(
                category=PrincipleCategory.EMPATHY,
                statement="Prioritize customer needs over sales targets",
                critique_prompt="Does this response prioritize customer needs or just closing the sale?",
                weight=1.3
            ),

            # Compliance principles
            Principle(
                category=PrincipleCategory.COMPLIANCE,
                statement="Follow all regulatory requirements",
                critique_prompt="Does this response violate any regulatory requirements?",
                weight=2.0
            ),
            Principle(
                category=PrincipleCategory.COMPLIANCE,
                statement="Maintain data privacy and security",
                critique_prompt="Does this response compromise data privacy or security?",
                weight=2.0
            ),
        ]

        return cls(principles=principles)


class ConstitutionalAI:
    """
    Constitutional AI 2.0

    实现价值对齐的AI系统：
    1. 定义伦理宪法
    2. 自我批评机制
    3. 迭代修正
    4. 对齐验证

    Usage:
        constitution = Constitution.create_sales_constitution()
        cai = ConstitutionalAI(constitution, llm_client)

        aligned_response = await cai.constitutional_generate(
            initial_response="Buy now or miss out!",
            context={"customer": "Acme Corp"}
        )
    """

    def __init__(
        self,
        constitution: Constitution,
        llm_client,
        max_iterations: int = 3,
        alignment_threshold: float = 0.8,
    ):
        """
        Initialize Constitutional AI

        Args:
            constitution: Ethical constitution
            llm_client: LLM client for generation and critique
            max_iterations: Max revision iterations
            alignment_threshold: Minimum alignment score
        """
        self.constitution = constitution
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.alignment_threshold = alignment_threshold

        # Statistics
        self.total_generations = 0
        self.total_revisions = 0
        self.alignment_violations = 0

        logger.info("ConstitutionalAI initialized with %d principles", len(constitution.principles))

    async def constitutional_generate(
        self,
        initial_response: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Constitutional generation with self-critique

        Steps:
        1. Start with initial response
        2. Critique against all principles
        3. If violations found, revise
        4. Repeat until aligned or max iterations

        Args:
            initial_response: Initial generated response
            context: Context information

        Returns:
            Dict with final_response, critiques, iterations, aligned
        """
        self.total_generations += 1
        context = context or {}

        response = initial_response
        all_critiques = []

        for iteration in range(self.max_iterations):
            logger.info(f"Constitutional iteration {iteration + 1}/{self.max_iterations}")

            # Critique against all principles
            critiques = await self._critique_response(response, context)
            all_critiques.append(critiques)

            # Calculate alignment score
            alignment_score = self._calculate_alignment_score(critiques)

            logger.info(f"Alignment score: {alignment_score:.2f}")

            # Check if aligned
            if alignment_score >= self.alignment_threshold:
                logger.info("Response aligned with constitution")
                return {
                    "final_response": response,
                    "critiques": all_critiques,
                    "iterations": iteration + 1,
                    "aligned": True,
                    "alignment_score": alignment_score,
                }

            # Find violations
            violations = [c for c in critiques if not c.aligned]

            if not violations:
                # All principles satisfied
                break

            # Revise response
            logger.info(f"Found {len(violations)} violations, revising...")
            self.total_revisions += 1
            self.alignment_violations += len(violations)

            response = await self._revise_response(
                response,
                violations,
                context
            )

        # Final alignment check
        final_critiques = await self._critique_response(response, context)
        final_alignment_score = self._calculate_alignment_score(final_critiques)

        return {
            "final_response": response,
            "critiques": all_critiques + [final_critiques],
            "iterations": self.max_iterations,
            "aligned": final_alignment_score >= self.alignment_threshold,
            "alignment_score": final_alignment_score,
        }

    async def _critique_response(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> List[Critique]:
        """
        Critique response against all principles

        Uses LLM to evaluate each principle
        """
        critiques = []

        for principle in self.constitution.principles:
            critique = await self._critique_single_principle(
                response,
                principle,
                context
            )
            critiques.append(critique)

        return critiques

    async def _critique_single_principle(
        self,
        response: str,
        principle: Principle,
        context: Dict[str, Any]
    ) -> Critique:
        """Critique against a single principle"""

        critique_prompt = f"""You are an ethical AI evaluator for sales conversations.

Principle: {principle.statement}
Category: {principle.category.value}

Response to evaluate: "{response}"

Context: {json.dumps(context, indent=2)}

Question: {principle.critique_prompt}

Evaluate whether the response aligns with this principle.

Output JSON:
{{
    "aligned": true/false,
    "confidence": 0.0-1.0,
    "reason": "detailed explanation",
    "suggested_revision": "how to fix if not aligned (or null if aligned)"
}}
"""

        try:
            # Call LLM for critique
            result = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": critique_prompt}],
                temperature=0.3,
            )

            # Parse response
            critique_data = self._parse_json_response(result.content)

            return Critique(
                principle=principle,
                aligned=critique_data.get("aligned", True),
                confidence=critique_data.get("confidence", 0.5),
                reason=critique_data.get("reason", ""),
                suggested_revision=critique_data.get("suggested_revision"),
            )

        except Exception as e:
            logger.error(f"Critique failed for principle {principle.statement}: {e}")
            # Default to aligned if critique fails
            return Critique(
                principle=principle,
                aligned=True,
                confidence=0.0,
                reason=f"Critique failed: {e}",
            )

    async def _revise_response(
        self,
        response: str,
        violations: List[Critique],
        context: Dict[str, Any]
    ) -> str:
        """
        Revise response to fix violations

        Uses LLM to generate improved response
        """
        violations_summary = "\n".join([
            f"- Principle: {v.principle.statement}\n"
            f"  Issue: {v.reason}\n"
            f"  Suggestion: {v.suggested_revision or 'N/A'}"
            for v in violations
        ])

        revision_prompt = f"""You are an ethical sales AI assistant.

Original response: "{response}"

Context: {json.dumps(context, indent=2)}

This response violates the following ethical principles:

{violations_summary}

Please revise the response to:
1. Fix all violations
2. Maintain sales effectiveness
3. Stay natural and conversational
4. Keep the core message

Output only the revised response (no JSON, no explanation).
"""

        try:
            result = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": revision_prompt}],
                temperature=0.5,
            )

            revised = result.content.strip()

            # Remove quotes if present
            if revised.startswith('"') and revised.endswith('"'):
                revised = revised[1:-1]

            logger.info(f"Revised response: {revised[:100]}...")

            return revised

        except Exception as e:
            logger.error(f"Revision failed: {e}")
            return response  # Return original if revision fails

    def _calculate_alignment_score(self, critiques: List[Critique]) -> float:
        """
        Calculate overall alignment score

        Weighted average of principle alignments
        """
        if not critiques:
            return 0.0

        total_weight = sum(c.principle.weight for c in critiques)

        weighted_score = sum(
            (1.0 if c.aligned else 0.0) * c.principle.weight * c.confidence
            for c in critiques
        )

        return weighted_score / total_weight if total_weight > 0 else 0.0

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        try:
            # Try to find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)

            # Fallback
            return {"aligned": True, "confidence": 0.5, "reason": "Parse failed"}

        except Exception as e:
            logger.error(f"JSON parse failed: {e}")
            return {"aligned": True, "confidence": 0.5, "reason": "Parse failed"}

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        return {
            "total_generations": self.total_generations,
            "total_revisions": self.total_revisions,
            "alignment_violations": self.alignment_violations,
            "avg_revisions_per_generation": self.total_revisions / max(self.total_generations, 1),
            "principles_count": len(self.constitution.principles),
        }
