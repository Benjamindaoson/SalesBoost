"""
Constitutional AI Integration Patch

This module integrates Constitutional AI into the main generation flow
as an optional post-processing step.

Usage:
    from ...engine.coordinator.constitutional_integration import apply_constitutional_ai

    # In your coordinator or agent
    raw_response = await llm.generate(prompt)

    # Apply Constitutional AI (optional)
    if enable_constitutional_ai:
        aligned_response = await apply_constitutional_ai(
            response=raw_response,
            context=context,
            llm_client=llm_client
        )
    else:
        aligned_response = raw_response
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


async def apply_constitutional_ai(
    response: str,
    context: Dict[str, Any],
    llm_client,
    max_iterations: int = 3,
    alignment_threshold: float = 0.8,
    enabled: bool = True
) -> Dict[str, Any]:
    """
    Apply Constitutional AI to align response with ethical principles

    Args:
        response: Raw LLM response
        context: Conversation context
        llm_client: LLM client for critique and revision
        max_iterations: Maximum critique-revision iterations
        alignment_threshold: Minimum alignment score to accept
        enabled: Whether Constitutional AI is enabled

    Returns:
        Dict with:
            - final_response: Aligned response
            - aligned: Whether response meets alignment threshold
            - alignment_score: Final alignment score
            - iterations: Number of iterations performed
            - original_response: Original response (for comparison)
    """

    if not enabled:
        return {
            "final_response": response,
            "aligned": True,
            "alignment_score": 1.0,
            "iterations": 0,
            "original_response": response,
            "constitutional_ai_applied": False
        }

    try:
        from ...ai_core.constitutional.constitutional_ai import (
            ConstitutionalAI,
            Constitution
        )

        # Create sales constitution
        constitution = Constitution.create_sales_constitution()

        # Initialize Constitutional AI
        cai = ConstitutionalAI(
            constitution=constitution,
            llm_client=llm_client,
            max_iterations=max_iterations,
            alignment_threshold=alignment_threshold
        )

        # Apply constitutional generation
        result = await cai.constitutional_generate(
            initial_response=response,
            context=context
        )

        # Add original response for comparison
        result["original_response"] = response
        result["constitutional_ai_applied"] = True

        # Log alignment result
        if result["aligned"]:
            logger.info(
                f"[ConstitutionalAI] Response aligned after {result['iterations']} iterations "
                f"(score: {result['alignment_score']:.2f})"
            )
        else:
            logger.warning(
                f"[ConstitutionalAI] Response NOT fully aligned after {result['iterations']} iterations "
                f"(score: {result['alignment_score']:.2f})"
            )

        return result

    except Exception as e:
        logger.error(f"[ConstitutionalAI] Error applying Constitutional AI: {e}")
        # Graceful degradation - return original response
        return {
            "final_response": response,
            "aligned": False,
            "alignment_score": 0.0,
            "iterations": 0,
            "original_response": response,
            "constitutional_ai_applied": False,
            "error": str(e)
        }


# Feature flag helper
def is_constitutional_ai_enabled() -> bool:
    """Check if Constitutional AI is enabled via feature flag"""
    try:
        from ...core.config import get_settings
        settings = get_settings()
        return getattr(settings, "CONSTITUTIONAL_AI_ENABLED", False)
    except:
        return False


# Example integration into NPC generator
async def generate_npc_response_with_constitutional_ai(
    message: str,
    history: list,
    persona: dict,
    stage: str,
    llm_client,
    enable_constitutional_ai: bool = None
) -> Dict[str, Any]:
    """
    Example: Generate NPC response with optional Constitutional AI

    This shows how to integrate Constitutional AI into existing generators
    """

    # Determine if Constitutional AI should be applied
    if enable_constitutional_ai is None:
        enable_constitutional_ai = is_constitutional_ai_enabled()

    # Generate raw response (existing logic)
    from ...agents.practice.npc_simulator import NPCGenerator
    npc_generator = NPCGenerator(model_gateway=llm_client)

    raw_result = await npc_generator.generate_response(
        message=message,
        history=history,
        persona=persona,
        stage=stage
    )

    # Apply Constitutional AI if enabled
    if enable_constitutional_ai:
        context = {
            "stage": stage,
            "persona": persona,
            "history": history
        }

        constitutional_result = await apply_constitutional_ai(
            response=raw_result.content,
            context=context,
            llm_client=llm_client,
            enabled=True
        )

        # Replace response with aligned version
        raw_result.content = constitutional_result["final_response"]
        raw_result.metadata = raw_result.metadata or {}
        raw_result.metadata["constitutional_ai"] = {
            "aligned": constitutional_result["aligned"],
            "alignment_score": constitutional_result["alignment_score"],
            "iterations": constitutional_result["iterations"],
            "original_response": constitutional_result["original_response"]
        }

    return raw_result


# Integration point for ProductionCoordinator
class ConstitutionalAIMiddleware:
    """
    Middleware to apply Constitutional AI to coordinator responses

    Usage in ProductionCoordinator:
        middleware = ConstitutionalAIMiddleware(llm_client, enabled=True)
        aligned_result = await middleware.process(raw_result, context)
    """

    def __init__(self, llm_client, enabled: bool = None):
        self.llm_client = llm_client
        self.enabled = enabled if enabled is not None else is_constitutional_ai_enabled()

    async def process(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process response through Constitutional AI"""
        return await apply_constitutional_ai(
            response=response,
            context=context,
            llm_client=self.llm_client,
            enabled=self.enabled
        )


# Configuration helper
def add_constitutional_ai_to_settings():
    """
    Add Constitutional AI configuration to settings

    Add this to core/config.py:

    class Settings(BaseSettings):
        ...
        # Constitutional AI
        CONSTITUTIONAL_AI_ENABLED: bool = Field(
            default=False,
            description="Enable Constitutional AI for value alignment"
        )
        CONSTITUTIONAL_AI_MAX_ITERATIONS: int = Field(
            default=3,
            description="Maximum critique-revision iterations"
        )
        CONSTITUTIONAL_AI_THRESHOLD: float = Field(
            default=0.8,
            ge=0.0,
            le=1.0,
            description="Minimum alignment score threshold"
        )
    """
    pass


if __name__ == "__main__":
    print("=" * 80)
    print("Constitutional AI Integration Module")
    print("=" * 80)
    print("\nThis module provides Constitutional AI integration for the main flow.")
    print("\nIntegration Steps:")
    print("1. Add CONSTITUTIONAL_AI_ENABLED to core/config.py")
    print("2. Import apply_constitutional_ai in your coordinator")
    print("3. Apply it as post-processing step after LLM generation")
    print("\nExample:")
    print("  raw_response = await llm.generate(prompt)")
    print("  aligned = await apply_constitutional_ai(raw_response, context, llm)")
    print("  final_response = aligned['final_response']")
    print("=" * 80)
