"""Memory service API endpoints."""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import date, datetime
import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import Text, and_, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_schemas import UserSchema as User
from api.deps import audit_access, require_user
from app.agents.roles.compliance_agent import ComplianceAgent
from app.infra.events.bus import bus
from app.infra.events.schemas import EventType, MemoryOutcomeEventPayload
from core.database import get_db_session
from models.memory_service_models import (
    MemoryAudit,
    MemoryEvent,
    MemoryKnowledge,
    MemoryOutcome,
    MemoryPersona,
    MemoryStrategyUnit,
)
from schemas.memory_service import (
    AuditTraceData,
    AuditTraceRequest,
    AuditTraceResponse,
    Citation,
    ComplianceAction,
    ComplianceCheckData,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ComplianceHit,
    ComplianceStatus,
    EventWriteData,
    EventWriteRequest,
    EventWriteResponse,
    KnowledgeWriteData,
    KnowledgeWriteRequest,
    KnowledgeWriteResponse,
    MemoryQueryData,
    MemoryQueryHit,
    MemoryQueryRequest,
    MemoryQueryResponse,
    OutcomeWriteData,
    OutcomeWriteRequest,
    OutcomeWriteResponse,
    PersonaWriteData,
    PersonaWriteRequest,
    PersonaWriteResponse,
    RouteDecision,
    StrategyWriteData,
    StrategyWriteRequest,
    StrategyWriteResponse,
)

try:
    from functools import lru_cache
except ImportError:  # pragma: no cover
    lru_cache = None  # type: ignore

try:
    from app.memory.storage.vector_store import VectorStore
except Exception:  # pragma: no cover
    VectorStore = None  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter(tags=["memory"], dependencies=[Depends(require_user), Depends(audit_access)])
compliance_agent = ComplianceAgent()


def _get_request_id(request: Request, fallback: str | None = None) -> str:
    return request.headers.get("x-request-id") or fallback or str(uuid.uuid4())


def _hash_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_date(value: Optional[str]) -> Optional[date]:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {value}") from exc


def _enforce_tenant(payload_tenant_id: str, current_user: User) -> str:
    if current_user.tenant_id and payload_tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return payload_tenant_id


def _route_from_hint(intent_hint: str | None, query: str | None) -> RouteDecision:
    hint = (intent_hint or "").lower()
    text = (query or "").lower()
    if any(key in hint for key in ["权益", "活动", "佣金"]):
        return RouteDecision.KNOWLEDGE
    if any(key in text for key in ["权益", "活动", "佣金"]):
        return RouteDecision.KNOWLEDGE
    if any(key in hint for key in ["异议", "sop", "推进"]):
        return RouteDecision.STRATEGY
    if any(key in text for key in ["异议", "sop", "推进"]):
        return RouteDecision.STRATEGY
    return RouteDecision.FALLBACK


if lru_cache:

    @lru_cache(maxsize=8)
    def _get_vector_store(collection_name: str):
        if VectorStore is None:
            return None
        try:
            return VectorStore(collection_name=collection_name)
        except Exception as exc:  # pragma: no cover
            logger.warning("VectorStore init failed: %s", exc)
            return None
else:  # pragma: no cover

    def _get_vector_store(collection_name: str):
        if VectorStore is None:
            return None
        try:
            return VectorStore(collection_name=collection_name)
        except Exception as exc:
            logger.warning("VectorStore init failed: %s", exc)
            return None


def _compact_json(data: object) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return str(data)


def _serialize_citations(citations: List[Citation]) -> List[dict]:
    return [item.dict() for item in citations]


def _compute_decay_score(last_used_at: Optional[datetime], base_decay: float = 1.0) -> float:
    """
    SOFC (Sales-Optimized Forgetting Curve) implementation.
    Score = base_decay * exp(-lambda * t)
    """
    if not last_used_at:
        return base_decay
    
    # Half-life of 7 days for sales context
    halflife_days = 7.0
    lam = math.log(2) / halflife_days
    
    days_passed = (datetime.utcnow() - last_used_at.replace(tzinfo=None)).total_seconds() / 86400.0
    decay = math.exp(-lam * days_passed)
    return base_decay * decay


def _rerank_hits(
    sql_hits: List[MemoryQueryHit], 
    vector_hits: List[MemoryQueryHit], 
    top_k: int,
    decay_weights: Dict[str, float] = None
) -> List[MemoryQueryHit]:
    """
    Enhanced RRF with Decay + Reactivation (Requirement 3).
    Score = sum(1 / (rank + k)) * decay_score
    """
    k = 60
    scores: Dict[str, float] = {}
    hit_map: Dict[str, MemoryQueryHit] = {}
    decay_weights = decay_weights or {}

    # SQL ranks
    for i, hit in enumerate(sql_hits):
        w = decay_weights.get(hit.id, 1.0)
        scores[hit.id] = scores.get(hit.id, 0) + (1.0 / (i + k)) * w
        hit_map[hit.id] = hit

    # Vector ranks
    for i, hit in enumerate(vector_hits):
        w = decay_weights.get(hit.id, 1.0)
        scores[hit.id] = scores.get(hit.id, 0) + (1.0 / (i + k)) * w
        if hit.id not in hit_map:
            hit_map[hit.id] = hit

    # Sort by RRF score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    
    final_hits = []
    for hit_id in sorted_ids[:top_k]:
        hit = hit_map[hit_id]
        hit.score = scores[hit_id]
        final_hits.append(hit)
    
    return final_hits


async def _cross_encode_rerank(
    query: str,
    hits: List[MemoryQueryHit],
    top_n: int = 5
) -> List[MemoryQueryHit]:
    """
    Task 2: Rerank Top-20 hits using BGE-Reranker or fallback to TinyBERT (Requirement 2).
    """
    if not hits or len(hits) <= 1:
        return hits[:top_n]

    try:
        from core.config import settings

        # Try BGE-Reranker first if enabled
        if settings.BGE_RERANKER_ENABLED:
            try:
                from app.infra.search.vector_store import BGEReranker, SearchResult

                # Convert MemoryQueryHit to SearchResult for BGE reranker
                search_results = [
                    SearchResult(
                        id=hit.id,
                        content=str(hit.content),
                        score=hit.score,
                        metadata={}
                    )
                    for hit in hits
                ]

                # Get BGE reranker instance and rerank
                reranker = BGEReranker.get_instance(
                    model_name=settings.BGE_RERANKER_MODEL,
                    batch_size=settings.BGE_RERANKER_BATCH_SIZE
                )
                reranked_results = reranker.rerank(query, search_results, top_k=top_n)

                # Convert back to MemoryQueryHit
                reranked_hits = []
                for result in reranked_results:
                    # Find original hit by ID
                    original_hit = next((h for h in hits if h.id == result.id), None)
                    if original_hit:
                        original_hit.score = result.score
                        reranked_hits.append(original_hit)

                logger.info(f"BGE reranking successful: {len(reranked_hits)} results")
                return reranked_hits

            except Exception as bge_error:
                logger.warning(f"BGE reranking failed, falling back to TinyBERT: {bge_error}")

        # Fallback to TinyBERT cross-encoder
        from sentence_transformers import CrossEncoder
        model = CrossEncoder('cross-encoder/ms-marco-TinyBERT-L-2-v2', max_length=512)

        pairs = [[query, str(hit.content)] for hit in hits]
        scores = model.predict(pairs)

        # Merge scores back to hits
        for hit, score in zip(hits, scores):
            hit.score = float(score)

        hits.sort(key=lambda x: x.score, reverse=True)
        logger.info(f"TinyBERT reranking successful: {len(hits[:top_n])} results")
        return hits[:top_n]

    except Exception as e:
        logger.warning(f"All reranking methods failed, returning RRF results: {e}")
        return hits[:top_n]


async def _fetch_evidence(db: AsyncSession, event_ids: List[str]) -> List[Dict[str, Any]]:
    if not event_ids:
        return []
    stmt = select(MemoryEvent).where(MemoryEvent.event_id.in_(event_ids))
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "event_id": r.event_id,
            "summary": r.summary,
            "stage": r.stage,
            "speaker": r.speaker
        }
        for r in rows
    ]


async def _write_audit(
    db: AsyncSession,
    request_id: str,
    tenant_id: str,
    user_id: Optional[str],
    session_id: Optional[str],
    route: Optional[str],
    retrieved_ids: List[str],
    citations: List[Citation],
    compliance_hits: Optional[List[str]] = None,
    input_digest: Optional[str] = None,
    output_digest: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    audit = MemoryAudit(
        request_id=request_id,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        input_digest=input_digest,
        route=route,
        retrieved_ids=retrieved_ids,
        citations=_serialize_citations(citations),
        compliance_hits=compliance_hits or [],
        output_digest=output_digest,
        metadata_json=metadata or {},
    )
    db.add(audit)


@router.post("/write/event", response_model=EventWriteResponse)
async def write_event(
    payload: EventWriteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
) -> EventWriteResponse:
    request_id = _get_request_id(request)
    tenant_id = _enforce_tenant(payload.tenant_id, current_user)

    event = MemoryEvent(
        event_id=payload.event_id,
        tenant_id=tenant_id,
        user_id=payload.user_id,
        session_id=payload.session_id,
        channel=payload.channel,
        turn_index=payload.turn_index,
        speaker=payload.speaker.value,
        raw_text_ref=payload.raw_text_ref,
        summary=payload.summary,
        intent_top1=payload.intent_top1,
        intent_topk=payload.intent_topk,
        stage=payload.stage,
        objection_type=payload.objection_type,
        entities=payload.entities,
        sentiment=payload.sentiment,
        tension=payload.tension,
        compliance_flags=payload.compliance_flags,
        coach_suggestions_shown=payload.coach_suggestions_shown,
        coach_suggestions_taken=payload.coach_suggestions_taken,
        metadata_json=payload.metadata,
    )
    db.add(event)

    stored = ["postgres"]
    if payload.summary:
        vector_store = _get_vector_store("memory_event_summary")
        if vector_store is not None:
            vector_store.add_documents(
                [payload.summary],
                [
                    {
                        "tenant_id": tenant_id,
                        "user_id": payload.user_id,
                        "session_id": payload.session_id,
                        "event_id": payload.event_id,
                        "speaker": payload.speaker.value,
                        "intent_top1": payload.intent_top1,
                        "stage": payload.stage,
                        "objection_type": payload.objection_type,
                    }
                ],
                [payload.event_id],
            )
            stored.append("vector")

    return EventWriteResponse(
        request_id=request_id,
        data=EventWriteData(event_id=payload.event_id, stored=stored),
    )


@router.post("/write/outcome", response_model=OutcomeWriteResponse)
async def write_outcome(
    payload: OutcomeWriteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
) -> OutcomeWriteResponse:
    request_id = _get_request_id(request)
    outcome_id = str(uuid.uuid4())
    tenant_id = current_user.tenant_id or "default"
    outcome = MemoryOutcome(
        outcome_id=outcome_id,
        tenant_id=tenant_id,
        session_id=payload.session_id,
        event_id=payload.event_id,
        adopted=payload.adopted,
        adopt_type=payload.adopt_type.value if payload.adopt_type else None,
        stage_before=payload.stage_before,
        stage_after=payload.stage_after,
        eval_scores=payload.eval_scores,
        compliance_result=payload.compliance_result,
        final_result=payload.final_result,
    )
    db.add(outcome)
    # Async stats update via event bus (idempotent handlers).
    strategy_ids: List[str] = []
    event_stmt = select(MemoryEvent).where(
        MemoryEvent.event_id == payload.event_id,
        MemoryEvent.tenant_id == tenant_id,
    )
    event_result = await db.execute(event_stmt)
    event = event_result.scalar_one_or_none()
    if event is not None:
        if event.coach_suggestions_taken:
            strategy_ids = list(event.coach_suggestions_taken)
        elif event.coach_suggestions_shown and payload.adopted:
            strategy_ids = list(event.coach_suggestions_shown)

    event_payload = MemoryOutcomeEventPayload(
        event_id=payload.event_id,
        outcome_id=outcome_id,
        adopted=payload.adopted,
        adopt_type=payload.adopt_type.value if payload.adopt_type else None,
        stage_before=payload.stage_before,
        stage_after=payload.stage_after,
        compliance_result=payload.compliance_result,
        final_result=payload.final_result,
        session_id=payload.session_id,
        user_id=current_user.id,
        tenant_id=tenant_id,
        strategy_ids=strategy_ids,
        request_id=request_id,
    )
    try:
        await bus.publish(EventType.MEMORY_OUTCOME_RECORDED, event_payload)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to publish outcome event: %s", exc)

    return OutcomeWriteResponse(
        request_id=request_id,
        data=OutcomeWriteData(outcome_id=outcome_id, adopted=payload.adopted),
    )


@router.post("/write/persona", response_model=PersonaWriteResponse)
async def write_persona(
    payload: PersonaWriteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
) -> PersonaWriteResponse:
    request_id = _get_request_id(request)
    tenant_id = current_user.tenant_id or "default"

    existing = await db.execute(
        select(MemoryPersona).where(
            MemoryPersona.tenant_id == tenant_id,
            MemoryPersona.user_id == payload.user_id,
        )
    )
    record = existing.scalar_one_or_none()
    if record is None:
        record = MemoryPersona(
            tenant_id=tenant_id,
            user_id=payload.user_id,
            level=payload.level,
            weakness_tags=payload.weakness_tags,
            last_eval_summary=payload.last_eval_summary,
            last_improvements=payload.last_improvements,
            next_actions=payload.next_actions,
            history_stats=payload.history_stats,
        )
        db.add(record)
    else:
        record.level = payload.level
        record.weakness_tags = payload.weakness_tags
        record.last_eval_summary = payload.last_eval_summary
        record.last_improvements = payload.last_improvements
        record.next_actions = payload.next_actions
        record.history_stats = payload.history_stats

    return PersonaWriteResponse(
        request_id=request_id,
        data=PersonaWriteData(user_id=payload.user_id, updated=True),
    )


@router.post("/write/knowledge", response_model=KnowledgeWriteResponse)
async def write_knowledge(
    payload: KnowledgeWriteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
) -> KnowledgeWriteResponse:
    request_id = _get_request_id(request)
    tenant_id = current_user.tenant_id or "default"

    existing = await db.execute(
        select(MemoryKnowledge).where(
            MemoryKnowledge.tenant_id == tenant_id,
            MemoryKnowledge.knowledge_id == payload.knowledge_id,
            MemoryKnowledge.version == payload.version,
        )
    )
    record = existing.scalar_one_or_none()
    if record is None:
        record = MemoryKnowledge(
            tenant_id=tenant_id,
            knowledge_id=payload.knowledge_id,
            version=payload.version,
            domain=payload.domain,
            product_id=payload.product_id,
            structured_content=payload.structured_content,
            source_ref=payload.source_ref,
            effective_from=_parse_date(payload.effective_from),
            effective_to=_parse_date(payload.effective_to),
            is_enabled=payload.is_enabled,
            citation_snippets=payload.citation_snippets,
            metadata_json=payload.metadata,
        )
        db.add(record)
    else:
        record.domain = payload.domain
        record.product_id = payload.product_id
        record.structured_content = payload.structured_content
        record.source_ref = payload.source_ref
        record.effective_from = _parse_date(payload.effective_from)
        record.effective_to = _parse_date(payload.effective_to)
        record.is_enabled = payload.is_enabled
        record.citation_snippets = payload.citation_snippets
        record.metadata_json = payload.metadata

    vector_store = _get_vector_store("memory_knowledge")
    if vector_store is not None:
        vector_store.add_documents(
            [_compact_json(payload.structured_content)],
            [
                {
                    "tenant_id": tenant_id,
                    "knowledge_id": payload.knowledge_id,
                    "domain": payload.domain,
                    "product_id": payload.product_id,
                    "version": payload.version,
                    "effective_from": payload.effective_from,
                    "effective_to": payload.effective_to,
                    "is_enabled": payload.is_enabled,
                    "source_ref": payload.source_ref,
                }
            ],
            [f"{payload.knowledge_id}:{payload.version}"],
        )

    return KnowledgeWriteResponse(
        request_id=request_id,
        data=KnowledgeWriteData(knowledge_id=payload.knowledge_id, version=payload.version),
    )


@router.post("/write/strategy", response_model=StrategyWriteResponse)
async def write_strategy(
    payload: StrategyWriteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
) -> StrategyWriteResponse:
    request_id = _get_request_id(request)
    tenant_id = current_user.tenant_id or "default"

    existing = await db.execute(
        select(MemoryStrategyUnit).where(
            MemoryStrategyUnit.tenant_id == tenant_id,
            MemoryStrategyUnit.strategy_id == payload.strategy_id,
        )
    )
    record = existing.scalar_one_or_none()
    if record is None:
        record = MemoryStrategyUnit(
            tenant_id=tenant_id,
            strategy_id=payload.strategy_id,
            type=payload.type,
            trigger_intent=payload.trigger_condition.intent,
            trigger_stage=payload.trigger_condition.stage,
            trigger_objection_type=payload.trigger_condition.objection_type,
            trigger_level=payload.trigger_condition.level,
            trigger_condition=payload.trigger_condition.dict(),
            steps=payload.steps,
            scripts=payload.scripts,
            dos_donts=payload.dos_donts,
            evidence_event_ids=payload.evidence_event_ids,
            stats=payload.stats,
            is_enabled=True,
        )
        db.add(record)
    else:
        record.type = payload.type
        record.trigger_intent = payload.trigger_condition.intent
        record.trigger_stage = payload.trigger_condition.stage
        record.trigger_objection_type = payload.trigger_condition.objection_type
        record.trigger_level = payload.trigger_condition.level
        record.trigger_condition = payload.trigger_condition.dict()
        record.steps = payload.steps
        record.scripts = payload.scripts
        record.dos_donts = payload.dos_donts
        record.evidence_event_ids = payload.evidence_event_ids
        record.stats = payload.stats

    vector_store = _get_vector_store("memory_strategy_unit")
    if vector_store is not None:
        vector_store.add_documents(
            [_compact_json({"steps": payload.steps, "scripts": payload.scripts})],
            [
                {
                    "tenant_id": tenant_id,
                    "strategy_id": payload.strategy_id,
                    "type": payload.type,
                    "trigger_intent": payload.trigger_condition.intent,
                    "trigger_stage": payload.trigger_condition.stage,
                    "trigger_objection_type": payload.trigger_condition.objection_type,
                    "trigger_level": payload.trigger_condition.level,
                }
            ],
            [payload.strategy_id],
        )

    return StrategyWriteResponse(
        request_id=request_id,
        data=StrategyWriteData(strategy_id=payload.strategy_id),
    )


@router.post("/query", response_model=MemoryQueryResponse)
async def query_memory(
    payload: MemoryQueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
) -> MemoryQueryResponse:
    request_id = _get_request_id(request)
    route = _route_from_hint(payload.intent_hint, payload.query)

    hits: List[MemoryQueryHit] = []
    sql_hits: List[MemoryQueryHit] = []
    vector_hits: List[MemoryQueryHit] = []
    citations: List[Citation] = []

    if route == RouteDecision.KNOWLEDGE:
        stmt = select(MemoryKnowledge).where(
            MemoryKnowledge.tenant_id == payload.tenant_id,
            MemoryKnowledge.is_enabled.is_(True),
        )
        if payload.intent_hint:
            stmt = stmt.where(MemoryKnowledge.domain.in_(["权益", "活动", "佣金"]))
        stmt = stmt.where(
            and_(
                MemoryKnowledge.effective_from <= date.today(),
                or_(MemoryKnowledge.effective_to.is_(None), MemoryKnowledge.effective_to >= date.today()),
            )
        )
        if payload.query:
            stmt = stmt.where(cast(MemoryKnowledge.structured_content, Text).ilike(f"%{payload.query}%"))
        stmt = stmt.order_by(MemoryKnowledge.updated_at.desc()).limit(payload.top_k)

        result = await db.execute(stmt)
        rows = result.scalars().all()

        decay_weights = {}
        for row in rows:
            sql_hits.append(
                MemoryQueryHit(
                    type="knowledge",
                    id=row.knowledge_id,
                    score=1.0,
                    content=row.structured_content,
                )
            )
            decay_weights[row.knowledge_id] = _compute_decay_score(row.last_used_at)

        vector_store = _get_vector_store("memory_knowledge")
        if vector_store is not None:
            v_results = vector_store.query(
                payload.query, 
                n_results=20, # Recall more for reranking
                filter_dict={"tenant_id": payload.tenant_id}
            )
            for item in v_results:
                meta = item.get("metadata") or {}
                knowledge_id = meta.get("knowledge_id")
                if knowledge_id:
                    vector_hits.append(
                        MemoryQueryHit(
                            type="knowledge",
                            id=knowledge_id,
                            score=float(item.get("distance", 0.0)),
                            content={"content": item.get("content")},
                        )
                    )

        # Hybrid Rerank with Decay
        initial_hits = _rerank_hits(sql_hits, vector_hits, top_k=20, decay_weights=decay_weights)
        
        # Task 2: Cross-Encoder 精排
        hits = await _cross_encode_rerank(payload.query, initial_hits, top_n=payload.top_k)
        
        # Build Citations & Update Reactivation
        hit_ids = [h.id for h in hits]
        stmt = select(MemoryKnowledge).where(
            MemoryKnowledge.knowledge_id.in_(hit_ids),
            MemoryKnowledge.tenant_id == payload.tenant_id
        )
        rows = (await db.execute(stmt)).scalars().all()
        row_map = {r.knowledge_id: r for r in rows}
        
        for hit in hits:
            row = row_map.get(hit.id)
            if row:
                # Requirement 3: Reactivation (再激活)
                row.last_used_at = datetime.utcnow()
                row.use_count += 1
                
                citations.append(
                    Citation(
                        type="knowledge",
                        id=row.knowledge_id,
                        version=row.version,
                        snippet=(row.citation_snippets[0] if row.citation_snippets else None),
                        source_ref=row.source_ref,
                    )
                )
        await db.commit()

    elif route == RouteDecision.STRATEGY:
        stmt = select(MemoryStrategyUnit).where(
            MemoryStrategyUnit.tenant_id == payload.tenant_id,
            MemoryStrategyUnit.is_enabled.is_(True),
        )
        if payload.stage:
            stmt = stmt.where(
                or_(
                    MemoryStrategyUnit.trigger_stage == payload.stage,
                    MemoryStrategyUnit.trigger_stage.is_(None),
                )
            )
        if payload.objection_type:
            stmt = stmt.where(
                or_(
                    MemoryStrategyUnit.trigger_objection_type == payload.objection_type,
                    MemoryStrategyUnit.trigger_objection_type.is_(None),
                )
            )
        if payload.intent_hint:
            stmt = stmt.where(
                or_(
                    MemoryStrategyUnit.trigger_intent == payload.intent_hint,
                    MemoryStrategyUnit.trigger_intent.is_(None),
                )
            )

        stmt = stmt.order_by(MemoryStrategyUnit.updated_at.desc()).limit(payload.top_k)
        result = await db.execute(stmt)
        rows = result.scalars().all()

        decay_weights = {}
        for row in rows:
            content = {"steps": row.steps, "scripts": row.scripts, "dos_donts": row.dos_donts}
            sql_hits.append(
                MemoryQueryHit(
                    type="strategy",
                    id=row.strategy_id,
                    score=1.0,
                    content=content,
                )
            )
            decay_weights[row.strategy_id] = _compute_decay_score(row.last_used_at)

        vector_store = _get_vector_store("memory_strategy_unit")
        if vector_store is not None:
            v_results = vector_store.query(
                payload.query, 
                n_results=20, # Recall more for reranking
                filter_dict={"tenant_id": payload.tenant_id}
            )
            for item in v_results:
                meta = item.get("metadata") or {}
                strategy_id = meta.get("strategy_id")
                if strategy_id:
                    vector_hits.append(
                        MemoryQueryHit(
                            type="strategy",
                            id=strategy_id,
                            score=float(item.get("distance", 0.0)),
                            content={"content": item.get("content")},
                        )
                    )

        # Hybrid Rerank with Decay
        initial_hits = _rerank_hits(sql_hits, vector_hits, top_k=20, decay_weights=decay_weights)
        
        # Task 2: Cross-Encoder 精排
        hits = await _cross_encode_rerank(payload.query, initial_hits, top_n=payload.top_k)
        
        # Fetch Strategy Metadata (Evidence & Stats) & Update Reactivation
        hit_ids = [h.id for h in hits]
        stmt = select(MemoryStrategyUnit).where(
            MemoryStrategyUnit.strategy_id.in_(hit_ids),
            MemoryStrategyUnit.tenant_id == payload.tenant_id
        )
        rows = (await db.execute(stmt)).scalars().all()
        row_map = {r.strategy_id: r for r in rows}
        
        for hit in hits:
            row = row_map.get(hit.id)
            if row:
                # Requirement 3: Reactivation (再激活)
                row.last_used_at = datetime.utcnow()
                row.use_count += 1

                # Evidence Index (Requirement 2.2)
                evidence = await _fetch_evidence(db, row.evidence_event_ids)
                hit.content["evidence"] = evidence
                hit.content["stats"] = row.stats
                
                citations.append(
                    Citation(
                        type="strategy",
                        id=row.strategy_id,
                        snippet=(row.scripts[0] if row.scripts else None),
                    )
                )
        await db.commit()

    input_digest = _hash_text(payload.query)
    output_digest = _hash_text(_compact_json({"hits": [hit.dict() for hit in hits]}))

    await _write_audit(
        db=db,
        request_id=request_id,
        tenant_id=payload.tenant_id,
        user_id=payload.user_id,
        session_id=payload.session_id,
        route=route.value,
        retrieved_ids=[hit.id for hit in hits],
        citations=citations,
        input_digest=input_digest,
        output_digest=output_digest,
        metadata={"route_policy": payload.route_policy},
    )

    return MemoryQueryResponse(
        request_id=request_id,
        data=MemoryQueryData(route_decision=route, hits=hits, citations=citations),
    )


@router.post("/comply/check", response_model=ComplianceCheckResponse)
async def compliance_check(
    payload: ComplianceCheckRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
) -> ComplianceCheckResponse:
    request_id = _get_request_id(request, payload.request_id)
    result = await compliance_agent.check(
        message=payload.candidate_response,
        context={
            "session_id": payload.session_id,
            "user_id": current_user.id,
            "tenant_id": current_user.tenant_id,
        },
    )

    hits: List[ComplianceHit] = [
        ComplianceHit(rule_id=flag.risk_type, reason="compliance_risk")
        for flag in result.risk_flags
    ]

    if result.risk_level == "BLOCK":
        status = ComplianceStatus.BLOCKED
        action = ComplianceAction.REWRITE
        safe_response = result.safe_rewrite
    else:
        status = ComplianceStatus.OK
        action = ComplianceAction.PASS
        safe_response = None

    await _write_audit(
        db=db,
        request_id=request_id,
        tenant_id=current_user.tenant_id or "default",
        user_id=current_user.id,
        session_id=payload.session_id,
        route="compliance",
        retrieved_ids=[],
        citations=payload.citations,
        compliance_hits=[hit.rule_id for hit in hits],
        input_digest=_hash_text(payload.candidate_response),
        output_digest=_hash_text(safe_response or payload.candidate_response),
    )

    return ComplianceCheckResponse(
        request_id=request_id,
        status=status,
        data=ComplianceCheckData(action=action, hits=hits, safe_response=safe_response),
    )


@router.post("/trace", response_model=AuditTraceResponse)
async def audit_trace(
    payload: AuditTraceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user),
) -> AuditTraceResponse:
    request_id = _get_request_id(request, payload.request_id)
    stmt = select(MemoryAudit).where(MemoryAudit.request_id == payload.request_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if record is None:
        return AuditTraceResponse(
            request_id=request_id,
            data=AuditTraceData(
                input_digest=None,
                route=None,
                retrieved_ids=[],
                citations=[],
                compliance_hits=[],
                output_digest=None,
            ),
        )

    citations = []
    for item in record.citations or []:
        try:
            citations.append(Citation(**item))
        except Exception:
            continue

    return AuditTraceResponse(
        request_id=request_id,
        data=AuditTraceData(
            input_digest=record.input_digest,
            route=record.route,
            retrieved_ids=record.retrieved_ids or [],
            citations=citations,
            compliance_hits=record.compliance_hits or [],
            output_digest=record.output_digest,
        ),
    )
