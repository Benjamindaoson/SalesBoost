"""Context Manager Engine for scoring, compression, and state sync."""
from __future__ import annotations

import asyncio
import logging
import uuid
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.context_manager.compression import compress_history, StructuredFacts
from app.context_manager.memory import ContextMemoryStore
from app.context_manager.scoring import compute_importance_score, ImportanceScores
from app.context_manager.state_sync import SalesStateStream
from app.context_manager.librarian import Librarian
from app.schemas.blackboard import DecisionTrace, StateConfidence
from app.infra.llm.adapters import AdapterFactory
from app.infra.gateway.schemas import ModelConfig
from app.infra.events.schemas import MemoryEventPayload
from app.services.memory_event_writer import record_event
from core.redis import get_redis

logger = logging.getLogger(__name__)


class ContextManagerEngine:
    def __init__(self):
        self.memory = ContextMemoryStore(max_s0=8)
        self.stream = SalesStateStream()
        self.librarian = Librarian()
        # Default model for context operations - fast and capable
        self.default_model_config = ModelConfig(
            provider="google",
            model_name="gemini-2.0-flash",
            temperature=0.3
        )

    async def process_turn(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str,
        turn_id: int,
        current_stage: Optional[str],
        previous_stage: Optional[str],
        user_input: str,
        npc_response: str,
        history_window: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        # Task 5: Distributed Lock (Requirement 6)
        redis = await get_redis()
        lock_key = f"lock:ctx:{session_id}"
        async with redis.lock(lock_key, timeout=10):
            blackboard = await self.librarian.get_blackboard(session_id=session_id, user_id=user_id)
            history = list(history_window) if history_window else []
            history.append({"role": "user", "content": user_input})
            history.append({"role": "npc", "content": npc_response})

            await self.memory.append_s0(session_id, {"role": "user", "content": user_input})
            await self.memory.append_s0(session_id, {"role": "npc", "content": npc_response})

            # Task 4: Load Previous Facts for Delta
            previous_facts = None
            try:
                s1_prev = await self.memory.read_json(f"ctx:s1:{session_id}")
                if s1_prev and "structured_facts" in s1_prev:
                    sf_data = s1_prev["structured_facts"]
                    previous_facts = StructuredFacts(**sf_data)
            except Exception:
                pass

            known_facts = []
            try:
                s2 = await self.memory.read_json(f"ctx:s2:{user_id}")
                known_facts = list(s2.values()) if isinstance(s2, dict) else []
            except Exception:
                known_facts = []

            # Get adapter for operations
            adapter = AdapterFactory.get_adapter(self.default_model_config.provider)
            
            # Module 1: Importance Scoring
            scores = await compute_importance_score(
                user_input=user_input,
                npc_response=npc_response,
                current_stage=current_stage,
                adapter=adapter,
                model_config=self.default_model_config,
                known_facts=known_facts,
            )

            # Module 2: 3-Channel Compression (Actionable Delta)
            compression = await compress_history(
                history=history,
                current_stage=current_stage,
                previous_stage=previous_stage,
                adapter=adapter,
                model_config=self.default_model_config,
                previous_facts=previous_facts, # Requirement 4
            )

            summary_payload = {
                "scores": scores.__dict__,
                "structured_facts": compression.structured_facts.to_dict(),
                "narrative_summary": compression.narrative_summary,
            }

            await self.memory.write_s1(session_id, summary_payload)

            # Module 3 & 4: State Logic and Persistence
            if scores.persistent:
                if compression.structured_facts.client_profile:
                    await self.memory.write_s2(user_id, compression.structured_facts.client_profile)
                if compression.structured_facts.objection_state:
                    await self.memory.write_s3(tenant_id, {"objection_patterns": compression.structured_facts.objection_state})

            # Compliance Block
            compliance_block = compression.compliance_hit or (scores.compliance_risk > 0.5)

            try:
                await self.librarian.estimate_state(blackboard, user_input=user_input, npc_response=npc_response)
                next_stage = compression.structured_facts.current_stage or current_stage
                if next_stage and next_stage != blackboard.stage_estimate.current:
                    blackboard.stage_estimate.previous = blackboard.stage_estimate.current
                    blackboard.stage_estimate.current = next_stage
                    blackboard.stage_estimate.transition_timestamp = datetime.utcnow()
                blackboard.stage_estimate.confidence = StateConfidence(value=0.7, method="compression")
                blackboard.history.append(
                    DecisionTrace(
                        turn_number=turn_id,
                        intent_detected=blackboard.last_intent or "unknown",
                        active_branch="context_manager",
                        mentor_candidates_count=0,
                        selected_strategy_id=None,
                        auditor_action="BLOCK" if compliance_block else "PASS",
                        reasoning=scores.reasoning if hasattr(scores, "reasoning") else "context update",
                    )
                )
                await self.librarian.save_blackboard(blackboard)
            except Exception as exc:
                logger.warning("Failed to update blackboard: %s", exc)

            # Task 4: Context Budget Control (Value-per-Token)
            # Requirement 7: Knapsack selection
            context_memory = self._assemble_context_knapsack(
                s0_buffer=await self.memory.get_s0(session_id),
                s1_summary=summary_payload,
                s2_profile_ref=f"ctx:s2:{user_id}",
                token_limit=1000
            )

            state = {
                "session_id": session_id,
                "turn_id": turn_id,
                "sales_stage": {
                    "current": compression.structured_facts.current_stage or current_stage,
                    "status": "In_Progress",
                    "last_transition_reason": "auto_update",
                },
                "training_goals": ["提升异议处理能力", "强化合规意识"],
                "context_memory": context_memory,
                "blackboard": blackboard.model_dump(mode="json"),
                "agent_flags": {
                    "compliance_block": compliance_block,
                    "coach_intervention_needed": False,
                    "npc_sentiment": "Neutral",
                },
            }

            try:
                await self.stream.publish(session_id, turn_id, state)
            except Exception as exc:
                logger.warning("Failed to publish sales state: %s", exc)

            if scores.persistent and scores.final_score >= 0.75:
                event_payload = MemoryEventPayload(
                    event_id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id,
                    turn_index=turn_id,
                    speaker="system",
                    summary=compression.narrative_summary,
                    intent_top1=next(iter(compression.structured_facts.objection_state.keys())) if compression.structured_facts.objection_state else None,
                    stage=compression.structured_facts.current_stage or current_stage,
                    objection_type=next(iter(compression.structured_facts.objection_state.keys())) if compression.structured_facts.objection_state else None,
                    compliance_flags=["risk"] if compliance_block else [],
                    metadata={
                        "scores": scores.__dict__,
                        "facts": compression.structured_facts.to_dict(),
                        "delta": compression.structured_facts.actionable_delta
                    }
                )
                asyncio.create_task(self._sync_persistent_memory(event_payload))

            return {
                "scores": scores,
                "summary": summary_payload,
                "state": state,
                "blackboard": blackboard,
            }

    async def _sync_persistent_memory(self, payload: MemoryEventPayload) -> None:
        try:
            await record_event(payload)
        except Exception as exc:
            logger.warning("Failed to persist memory event %s: %s", payload.event_id, exc)
            await self._mark_pending_sync(payload, str(exc))

    async def _mark_pending_sync(self, payload: MemoryEventPayload, error: str) -> None:
        redis = await get_redis()
        key = f"memory:pending_sync:{payload.event_id}"
        data = {
            "status": "pending_sync",
            "event": payload.model_dump(),
            "error": error,
        }
        try:
            await redis.set(key, json.dumps(data, ensure_ascii=True), ex=60 * 60 * 24)
        except Exception as exc:
            logger.warning("Failed to set pending_sync key: %s", exc)

    def _assemble_context_knapsack(
        self, 
        s0_buffer: List[Dict], 
        s1_summary: Dict, 
        s2_profile_ref: str,
        token_limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Requirement 7: Knapsack selection for context (Value-per-Token).
        """
        # Simplified token estimation
        def estimate_tokens(obj):
            return len(str(obj)) // 4
        
        # Define candidate items with values and weights
        # Value logic: S1 (Summary) is highest, S0 (Recent) is high, S2 (Profile) is medium
        candidates = [
            {"id": "s1", "data": s1_summary, "value": 100, "weight": estimate_tokens(s1_summary)},
            {"id": "s2_ref", "data": s2_profile_ref, "value": 50, "weight": 10},
        ]
        
        # Add S0 messages individually
        for i, msg in enumerate(reversed(s0_buffer)):
            candidates.append({
                "id": f"s0_{i}", 
                "data": msg, 
                "value": 80 - (i * 10), # Older messages have less value
                "weight": estimate_tokens(msg)
            })
            
        # Greedy Knapsack (Value per Weight)
        for item in candidates:
            item["vpw"] = item["value"] / max(1, item["weight"])
            
        candidates.sort(key=lambda x: x["vpw"], reverse=True)
        
        selected = {}
        current_weight = 0
        s0_selected = []
        
        for item in candidates:
            if current_weight + item["weight"] <= token_limit:
                if item["id"].startswith("s0_"):
                    s0_selected.append(item["data"])
                else:
                    selected[item["id"]] = item["data"]
                current_weight += item["weight"]
                
        selected["s0_buffer"] = list(reversed(s0_selected))
        return selected
