"""
Data Flywheel Service

Extracts winning patterns from closed-won deals and feeds them back
into the knowledge base, creating a virtuous cycle:

  Win deal → Extract what worked → Improve RAG → Next deal does better

Key capabilities:
- Extract best-practice talk tracks from won deals
- Rank talk-track effectiveness by conversion correlation
- Generate "winning playbook" entries per methodology dimension
- Detect anti-patterns from lost deals
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.deal import Deal, DealStage, Encounter
from ..models.message import Message
from ..models.session import Session
from ..models.evaluation import Evaluation
from .methodology_engine import MethodologyState, FRAMEWORK_DEFINITIONS, DimensionStatus

logger = logging.getLogger(__name__)


class DataFlywheel:
    """
    Service that turns closed deals into organizational knowledge.
    """

    @staticmethod
    async def extract_winning_patterns(
        db: AsyncSession,
        tenant_id: str = "default",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Analyze closed-won deals to extract what methodology dimensions
        and talk tracks correlated with success.
        """
        stmt = (
            select(Deal)
            .where(
                and_(
                    Deal.stage == DealStage.CLOSED_WON,
                    Deal.tenant_id == tenant_id,
                )
            )
            .order_by(Deal.updated_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        won_deals = result.scalars().all()

        patterns: List[Dict[str, Any]] = []

        for deal in won_deals:
            if not deal.methodology_state:
                continue

            state = MethodologyState.from_json(deal.methodology_state)

            confirmed_dims = [
                k for k, v in state.dimensions.items()
                if v.status == DimensionStatus.CONFIRMED
            ]

            evidence_map = {
                k: v.evidence
                for k, v in state.dimensions.items()
                if v.evidence
            }

            patterns.append({
                "deal_id": deal.id,
                "customer_name": deal.customer_name,
                "amount": deal.amount,
                "framework": state.framework,
                "final_score": state.overall_score,
                "confirmed_dimensions": confirmed_dims,
                "evidence": evidence_map,
                "close_reason": deal.close_reason,
            })

        return patterns

    @staticmethod
    async def extract_losing_patterns(
        db: AsyncSession,
        tenant_id: str = "default",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Analyze closed-lost deals to find common missing dimensions (anti-patterns).
        """
        stmt = (
            select(Deal)
            .where(
                and_(
                    Deal.stage == DealStage.CLOSED_LOST,
                    Deal.tenant_id == tenant_id,
                )
            )
            .order_by(Deal.updated_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        lost_deals = result.scalars().all()

        missing_counts: Dict[str, int] = {}
        total = 0

        for deal in lost_deals:
            if not deal.methodology_state:
                continue
            total += 1
            state = MethodologyState.from_json(deal.methodology_state)

            for k, v in state.dimensions.items():
                if v.status == DimensionStatus.UNKNOWN:
                    missing_counts[k] = missing_counts.get(k, 0) + 1

        anti_patterns = []
        if total > 0:
            for dim, count in sorted(missing_counts.items(), key=lambda x: -x[1]):
                pct = round((count / total) * 100, 1)
                anti_patterns.append({
                    "dimension": dim,
                    "missing_pct": pct,
                    "missing_count": count,
                    "total_lost": total,
                    "insight": f"{pct}% 的输单商机未确认 {dim}",
                })

        return anti_patterns

    @staticmethod
    async def rank_talk_tracks(
        db: AsyncSession,
        tenant_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """
        Rank methodology dimensions by how strongly they correlate
        with winning. Dimensions confirmed in most won deals rank highest.
        """
        won_stmt = select(Deal).where(
            and_(Deal.stage == DealStage.CLOSED_WON, Deal.tenant_id == tenant_id)
        )
        won_result = await db.execute(won_stmt)
        won_deals = won_result.scalars().all()

        dim_confirmed_in_wins: Dict[str, int] = {}
        total_wins = 0

        for deal in won_deals:
            if not deal.methodology_state:
                continue
            total_wins += 1
            state = MethodologyState.from_json(deal.methodology_state)
            for k, v in state.dimensions.items():
                if v.status == DimensionStatus.CONFIRMED:
                    dim_confirmed_in_wins[k] = dim_confirmed_in_wins.get(k, 0) + 1

        rankings = []
        if total_wins > 0:
            defn = FRAMEWORK_DEFINITIONS.get("meddpicc", {}).get("dimensions", {})
            for dim, count in sorted(dim_confirmed_in_wins.items(), key=lambda x: -x[1]):
                pct = round((count / total_wins) * 100, 1)
                label = defn.get(dim, {}).get("label", dim)
                rankings.append({
                    "dimension": dim,
                    "label": label,
                    "win_correlation_pct": pct,
                    "confirmed_in_wins": count,
                    "total_wins": total_wins,
                })

        return rankings

    @staticmethod
    async def generate_playbook_entries(
        db: AsyncSession,
        tenant_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """
        Generate playbook entries from winning deal evidence.
        These can be fed back into the RAG knowledge base.
        """
        patterns = await DataFlywheel.extract_winning_patterns(db, tenant_id)

        entries: List[Dict[str, Any]] = []
        dim_evidence_collection: Dict[str, List[str]] = {}

        for p in patterns:
            for dim, evidence in p.get("evidence", {}).items():
                if evidence:
                    if dim not in dim_evidence_collection:
                        dim_evidence_collection[dim] = []
                    dim_evidence_collection[dim].append(evidence)

        defn = FRAMEWORK_DEFINITIONS.get("meddpicc", {}).get("dimensions", {})
        for dim, evidences in dim_evidence_collection.items():
            label = defn.get(dim, {}).get("label", dim)
            entries.append({
                "type": "playbook",
                "dimension": dim,
                "label": label,
                "title": f"赢单最佳实践 — {label}",
                "content": "\n".join(f"- {e}" for e in evidences[:10]),
                "source": "data_flywheel",
                "entry_count": len(evidences),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })

        return entries

    @staticmethod
    async def get_flywheel_summary(
        db: AsyncSession,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Complete flywheel summary for the cockpit.
        """
        winning = await DataFlywheel.extract_winning_patterns(db, tenant_id, limit=100)
        losing = await DataFlywheel.extract_losing_patterns(db, tenant_id, limit=100)
        rankings = await DataFlywheel.rank_talk_tracks(db, tenant_id)
        playbook = await DataFlywheel.generate_playbook_entries(db, tenant_id)

        return {
            "winning_patterns_count": len(winning),
            "losing_patterns_count": len(losing),
            "top_anti_patterns": losing[:3],
            "dimension_rankings": rankings[:8],
            "playbook_entries": len(playbook),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
