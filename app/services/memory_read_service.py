import logging
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.memory import MemoryContext, MemorySnippet, ReflectiveAction, TurnState
from app.models.memory_models import MemoryItem, MemoryStatus, MemoryScope, MemoryType, ReflectiveRule, RuleStatus

logger = logging.getLogger(__name__)


class MemoryReadService:
    """Read-only memory context builder for Fast Path."""

    def __init__(self, max_snippets: int = 6, max_rules: int = 6):
        self.max_snippets = max_snippets
        self.max_rules = max_rules
        self.scope_order = [
            MemoryScope.USER,
            MemoryScope.SCENARIO,
            MemoryScope.ORG,
            MemoryScope.GLOBAL,
        ]
        self.scope_quota = {
            MemoryScope.USER: 2,
            MemoryScope.SCENARIO: 2,
            MemoryScope.ORG: 1,
            MemoryScope.GLOBAL: 1,
        }

    async def get_context(
        self,
        turn_state: TurnState,
        db: Optional[AsyncSession],
    ) -> MemoryContext:
        if db is None:
            return MemoryContext()

        semantic_snippets = await self._load_semantic_memory(turn_state, db)
        reflective_actions = await self._load_reflective_rules(turn_state, db)

        provenance = [
            {
                "type": "semantic",
                "memory_id": snippet.memory_id,
                "scope": snippet.scope.value,
                "scope_id": snippet.scope_id,
                "source_episode_id": snippet.source_episode_id,
            }
            for snippet in semantic_snippets
        ] + [
            {
                "type": "reflective",
                "rule_id": action.rule_id,
                "scope": action.scope.value,
                "scope_id": action.scope_id,
            }
            for action in reflective_actions
        ]

        return MemoryContext(
            semantic_snippets=semantic_snippets,
            reflective_actions=reflective_actions,
            provenance=provenance,
        )

    async def _load_semantic_memory(
        self,
        turn_state: TurnState,
        db: AsyncSession,
    ) -> List[MemorySnippet]:
        snippets: List[MemorySnippet] = []
        for scope in self.scope_order:
            if len(snippets) >= self.max_snippets:
                break
            scope_id = self._resolve_scope_id(scope, turn_state)
            if scope_id is None and scope != MemoryScope.GLOBAL:
                continue
            quota = self.scope_quota.get(scope, 1)
            fetched = await self._fetch_memory_items(
                db,
                turn_state=turn_state,
                scope=scope,
                scope_id=scope_id,
                limit=min(quota, self.max_snippets - len(snippets)),
            )
            snippets.extend(fetched)
        return snippets

    async def _fetch_memory_items(
        self,
        db: AsyncSession,
        *,
        turn_state: TurnState,
        scope: MemoryScope,
        scope_id: Optional[str],
        limit: int,
    ) -> List[MemorySnippet]:
        filters = [
            MemoryItem.memory_type == MemoryType.SEMANTIC,
            MemoryItem.status == MemoryStatus.ACTIVE,
            MemoryItem.scope == scope,
        ]
        if scope == MemoryScope.GLOBAL:
            filters.append(MemoryItem.tenant_id.is_(None))
        elif turn_state.tenant_id:
            filters.append(MemoryItem.tenant_id == turn_state.tenant_id)

        if scope == MemoryScope.GLOBAL:
            filters.append(MemoryItem.scope_id.is_(None))
        else:
            filters.append(MemoryItem.scope_id == scope_id)

        stmt = (
            select(MemoryItem)
            .where(*filters)
            .order_by(desc(MemoryItem.updated_at))
            .limit(limit)
        )
        results = await db.execute(stmt)
        items = results.scalars().all()
        return [
            MemorySnippet(
                memory_id=item.memory_id,
                title=item.title,
                content=item.content,
                tags=list(item.tags or []),
                confidence=item.confidence,
                scope=item.scope,
                scope_id=item.scope_id,
                source_episode_id=item.source_episode_id,
            )
            for item in items
        ]

    async def _load_reflective_rules(
        self,
        turn_state: TurnState,
        db: AsyncSession,
    ) -> List[ReflectiveAction]:
        actions: List[ReflectiveAction] = []
        for scope in self.scope_order:
            if len(actions) >= self.max_rules:
                break
            scope_id = self._resolve_scope_id(scope, turn_state)
            if scope_id is None and scope != MemoryScope.GLOBAL:
                continue
            quota = self.scope_quota.get(scope, 1)
            fetched = await self._fetch_reflective_rules(
                db,
                turn_state=turn_state,
                scope=scope,
                scope_id=scope_id,
                limit=min(quota, self.max_rules - len(actions)),
            )
            actions.extend(fetched)
        actions.sort(key=lambda a: a.priority, reverse=True)
        return actions

    async def _fetch_reflective_rules(
        self,
        db: AsyncSession,
        *,
        turn_state: TurnState,
        scope: MemoryScope,
        scope_id: Optional[str],
        limit: int,
    ) -> List[ReflectiveAction]:
        filters = [
            ReflectiveRule.status == RuleStatus.ACTIVE,
            ReflectiveRule.scope == scope,
        ]
        if scope == MemoryScope.GLOBAL:
            filters.append(ReflectiveRule.tenant_id.is_(None))
        elif turn_state.tenant_id:
            filters.append(ReflectiveRule.tenant_id == turn_state.tenant_id)

        if scope == MemoryScope.GLOBAL:
            filters.append(ReflectiveRule.scope_id.is_(None))
        else:
            filters.append(ReflectiveRule.scope_id == scope_id)

        stmt = (
            select(ReflectiveRule)
            .where(*filters)
            .order_by(desc(ReflectiveRule.priority), desc(ReflectiveRule.updated_at))
            .limit(limit * 2)
        )
        results = await db.execute(stmt)
        candidates = results.scalars().all()
        actions: List[ReflectiveAction] = []
        for rule in candidates:
            if not self._match_trigger(rule.trigger or {}, turn_state):
                continue
            actions.append(
                ReflectiveAction(
                    rule_id=rule.rule_id,
                    trigger=rule.trigger or {},
                    action=rule.action or {},
                    priority=rule.priority,
                    scope=rule.scope,
                    scope_id=rule.scope_id,
                    explain=rule.explain,
                )
            )
            if len(actions) >= limit:
                break
        return actions

    def _resolve_scope_id(self, scope: MemoryScope, turn_state: TurnState) -> Optional[str]:
        if scope == MemoryScope.USER:
            return turn_state.user_id
        if scope == MemoryScope.SCENARIO:
            return turn_state.scenario_id
        if scope == MemoryScope.ORG:
            return turn_state.tenant_id
        return None

    def _match_trigger(self, trigger: dict, turn_state: TurnState) -> bool:
        if not trigger:
            return True
        mappings = {
            "stage": turn_state.stage,
            "scenario_id": turn_state.scenario_id,
            "persona_id": turn_state.persona_id,
            "user_id": turn_state.user_id,
            "tenant_id": turn_state.tenant_id,
        }
        for key, expected in trigger.items():
            actual = mappings.get(key)
            if expected is None:
                continue
            if actual != expected:
                return False
        return True
