import logging
import random
from typing import List, Optional
from app.infra.gateway.schemas import ModelConfig, RoutingContext, AgentType, LatencyMode
from app.infra.llm.interfaces import RoutingStrategy
from app.infra.llm.registry import model_registry, ModelMetadata

logger = logging.getLogger(__name__)

class SmartRouter(RoutingStrategy):
    """
    Intelligent Routing Engine.
    Optimizes for Cost, Latency, and Quality based on Context.
    """

    def select_model(self, context: RoutingContext, candidates: List[ModelConfig] = None, prompt: str = None) -> ModelConfig:
        # 1. Get all available models from registry if candidates not provided
        all_models = model_registry.list_models()
        
        # 2. Filter based on hard constraints
        valid_models = self._filter_models(context, all_models)
        
        if not valid_models:
            logger.warning(f"No models met constraints for {context}. Falling back to default.")
            # Fallback to a safe default (usually the cheapest/fastest reliable one)
            return ModelConfig(provider="google", model_name="gemini-2.0-flash")

        # 3. Score models (with optional prompt intent)
        best_model = self._score_models(context, valid_models, prompt)
        
        logger.info(f"Routed {context.agent_type} to {best_model.provider}/{best_model.model_name}")
        return ModelConfig(
            provider=best_model.provider,
            model_name=best_model.model_name
        )

    def select_shadow_model(self, context: RoutingContext, primary_model: ModelConfig) -> Optional[ModelConfig]:
        """
        Select a shadow model for A/B testing or validation.
        Returns None if no shadow test should be run.
        """
        # 1. Random sample (10% of traffic for Gradual Rollout)
        if random.random() >= 0.1:
            return None
            
        # 2. Pick a candidate that is NOT the primary
        all_models = model_registry.list_models()
        valid_models = self._filter_models(context, all_models)
        
        candidates = [m for m in valid_models if m.status == "SHADOW" and m.model_name != primary_model.model_name]
        
        if not candidates:
            return None
            
        # 3. Pick one randomly
        shadow = random.choice(candidates)
        
        return ModelConfig(
            provider=shadow.provider,
            model_name=shadow.model_name
        )

    def _filter_models(self, context: RoutingContext, models: List[ModelMetadata]) -> List[ModelMetadata]:
        filtered = []
        for m in models:
            if m.status in {"QUARANTINED", "SHADOW"}:
                continue
            # Availability Check (Circuit Breaker)
            if m.success_rate < 0.8:
                continue

            # Risk/Compliance Check
            if context.risk_level == "high" and m.quality_score < 9.0:
                continue
            
            # Budget Check
            # If budget is critical (< $0.01), block expensive models
            if context.budget_remaining < 0.01 and m.input_cost_per_1k > 0.001:
                continue

            # Latency Check
            if context.latency_mode == LatencyMode.FAST and m.avg_latency_ms > 1000:
                continue

            filtered.append(m)
        
        return filtered

    def _score_models(self, context: RoutingContext, models: List[ModelMetadata], prompt: str = None) -> ModelMetadata:
        # Define weights based on AgentType (Base Baseline)
        w_quality = 1.0
        w_cost = 1.0
        w_latency = 1.0

        # Dynamic Weight Adjustment based on Agent Type
        if context.agent_type in [AgentType.COACH, AgentType.EVALUATOR, AgentType.STRATEGY]:
            w_quality = 4.0  # Quality is paramount for coaching
            w_cost = 0.2
            w_latency = 0.5
        elif context.agent_type in [AgentType.INTENT_GATE, AgentType.NPC]:
            w_quality = 1.0
            w_cost = 2.0     # Cost/Latency matters more for high-frequency nodes
            w_latency = 3.0
        elif context.agent_type == "sdr": # New Autonomous Agent
            w_quality = 2.5
            w_cost = 1.0
            w_latency = 1.0

        # Model Cascade Logic (Tiered Routing)
        # We classify intents into complexity tiers to force-route to appropriate models
        
        # Heuristic: Simple intents should utilize Tier 1 (Fast/Cheap) models
        # This significantly reduces cost and latency for trivial interactions.
        is_simple_intent = False
        if prompt:
             # Very basic heuristic - in production this would be the Intent Classifier's output
             prompt_lower = prompt.lower()
             if len(prompt) < 20 or any(x in prompt_lower for x in ["hi", "hello", "yes", "no", "ok", "bye", "thanks"]):
                 is_simple_intent = True
        
        scored_models = []
        for m in models:
            # 1. Normalize metrics (0-1 scale)
            # Latency: lower is better. 2000ms is "slow" baseline.
            s_latency = max(0, 1 - (m.avg_latency_ms / 2000.0))
            
            # Cost: lower is better. $0.01 is "expensive" baseline.
            s_cost = max(0, 1 - (m.input_cost_per_1k / 0.01))
            
            # Quality: higher is better. 10.0 is max.
            s_quality = m.quality_score / 10.0
            
            # 2. Apply Cascade Penalties/Bonuses
            bonus = 0.0
            
            # If simple intent, heavily penalize slow/expensive models
            if is_simple_intent:
                if m.avg_latency_ms > 500 or m.input_cost_per_1k > 0.001:
                    bonus -= 5.0 # Strong penalty to force cheap model
                else:
                    bonus += 2.0 # Bonus for fit
            
            # If reasoning required (Coach), penalize dumb models
            if context.agent_type == AgentType.COACH:
                if m.quality_score < 8.0:
                    bonus -= 5.0
            
            # 3. Calculate Final Score
            final_score = (s_quality * w_quality) + (s_cost * w_cost) + (s_latency * w_latency) + bonus
            
            scored_models.append((final_score, m))
            
        # Sort by score descending
        scored_models.sort(key=lambda x: x[0], reverse=True)
        
        best_model = scored_models[0][1]
        logger.debug(f"Router scored {len(models)} models. Winner: {best_model.provider}/{best_model.model_name} (Score: {scored_models[0][0]:.2f})")
        
        return best_model


router = SmartRouter()
