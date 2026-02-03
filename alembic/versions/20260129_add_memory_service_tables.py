"""add memory service tables

Revision ID: 20260129_memory_service
Revises: 20260127_add_message_turn_status
Create Date: 2026-01-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260129_memory_service"
down_revision: Union[str, Sequence[str], None] = "20260127_add_message_turn_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _dialect_name() -> str:
    bind = op.get_bind()
    if bind is not None:
        return bind.dialect.name
    try:
        return context.get_context().dialect.name
    except Exception:
        return "postgresql"


def _json_type(dialect: str) -> sa.types.TypeEngine:
    if dialect == "postgresql":
        return postgresql.JSONB()
    return sa.JSON()


def _array_type(item_type: sa.types.TypeEngine, dialect: str) -> sa.types.TypeEngine:
    if dialect == "postgresql":
        return postgresql.ARRAY(item_type)
    return sa.JSON()


def upgrade() -> None:
    dialect = _dialect_name()
    json_type = _json_type(dialect)
    array_text = _array_type(sa.Text(), dialect)
    array_str = _array_type(sa.String(), dialect)

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    bool_default = sa.text("true") if dialect == "postgresql" else sa.text("1")

    op.create_table(
        "memory_event",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=True),
        sa.Column("turn_index", sa.Integer(), nullable=True),
        sa.Column("speaker", sa.Text(), nullable=False),
        sa.Column("raw_text_ref", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("intent_top1", sa.Text(), nullable=True),
        sa.Column("intent_topk", array_text, nullable=True),
        sa.Column("stage", sa.Text(), nullable=True),
        sa.Column("objection_type", sa.Text(), nullable=True),
        sa.Column("entities", array_text, nullable=True),
        sa.Column("sentiment", sa.Text(), nullable=True),
        sa.Column("tension", sa.Numeric(4, 3), nullable=True),
        sa.Column("compliance_flags", array_text, nullable=True),
        sa.Column("coach_suggestions_shown", array_text, nullable=True),
        sa.Column("coach_suggestions_taken", array_text, nullable=True),
        sa.Column("metadata", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index(
        "idx_event_tenant_user_session",
        "memory_event",
        ["tenant_id", "user_id", "session_id", "created_at"],
    )
    op.create_index("idx_event_intent", "memory_event", ["tenant_id", "intent_top1"])
    op.create_index("idx_event_stage", "memory_event", ["tenant_id", "stage"])

    if dialect == "postgresql":
        op.create_index(
            "idx_event_intent_topk_gin",
            "memory_event",
            ["intent_topk"],
            postgresql_using="gin",
        )
        op.create_index(
            "idx_event_entities_gin",
            "memory_event",
            ["entities"],
            postgresql_using="gin",
        )
        op.create_index(
            "idx_event_compliance_gin",
            "memory_event",
            ["compliance_flags"],
            postgresql_using="gin",
        )
        op.create_index(
            "idx_event_suggest_shown_gin",
            "memory_event",
            ["coach_suggestions_shown"],
            postgresql_using="gin",
        )
        op.create_index(
            "idx_event_suggest_taken_gin",
            "memory_event",
            ["coach_suggestions_taken"],
            postgresql_using="gin",
        )

    server_default_uuid = sa.text("gen_random_uuid()") if dialect == "postgresql" else None
    outcome_id_type = postgresql.UUID(as_uuid=True) if dialect == "postgresql" else sa.String(36)

    op.create_table(
        "memory_outcome",
        sa.Column("outcome_id", outcome_id_type, primary_key=True, server_default=server_default_uuid),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("adopted", sa.Boolean(), nullable=False),
        sa.Column("adopt_type", sa.Text(), nullable=True),
        sa.Column("stage_before", sa.Text(), nullable=True),
        sa.Column("stage_after", sa.Text(), nullable=True),
        sa.Column("eval_scores", json_type, nullable=True),
        sa.Column("compliance_result", sa.Text(), nullable=True),
        sa.Column("final_result", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["event_id"], ["memory_event.event_id"]),
    )
    op.create_index("idx_outcome_tenant_session", "memory_outcome", ["tenant_id", "session_id", "created_at"])
    op.create_index("idx_outcome_event", "memory_outcome", ["tenant_id", "event_id"])

    op.create_table(
        "memory_persona",
        sa.Column("tenant_id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), primary_key=True),
        sa.Column("level", sa.Text(), nullable=True),
        sa.Column("weakness_tags", array_text, nullable=True),
        sa.Column("last_eval_summary", sa.Text(), nullable=True),
        sa.Column("last_improvements", array_text, nullable=True),
        sa.Column("next_actions", array_text, nullable=True),
        sa.Column("history_stats", json_type, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    if dialect == "postgresql":
        op.create_index(
            "idx_persona_weakness_gin",
            "memory_persona",
            ["weakness_tags"],
            postgresql_using="gin",
        )

    op.create_table(
        "memory_knowledge",
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("knowledge_id", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("product_id", sa.Text(), nullable=True),
        sa.Column("structured_content", json_type, nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=bool_default),
        sa.Column("citation_snippets", array_text, nullable=True),
        sa.Column("metadata", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("tenant_id", "knowledge_id", "version"),
    )
    op.create_index(
        "idx_knowledge_lookup",
        "memory_knowledge",
        ["tenant_id", "domain", "product_id", "is_enabled"],
    )
    op.create_index(
        "idx_knowledge_effective",
        "memory_knowledge",
        ["tenant_id", "effective_from", "effective_to"],
    )

    op.create_table(
        "memory_strategy_unit",
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("strategy_id", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("trigger_intent", sa.Text(), nullable=True),
        sa.Column("trigger_stage", sa.Text(), nullable=True),
        sa.Column("trigger_objection_type", sa.Text(), nullable=True),
        sa.Column("trigger_level", sa.Text(), nullable=True),
        sa.Column("trigger_condition", json_type, nullable=True),
        sa.Column("steps", array_text, nullable=True),
        sa.Column("scripts", array_text, nullable=True),
        sa.Column("dos_donts", json_type, nullable=True),
        sa.Column("evidence_event_ids", array_text, nullable=True),
        sa.Column("stats", json_type, nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=bool_default),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("tenant_id", "strategy_id"),
    )
    op.create_index("idx_strategy_type", "memory_strategy_unit", ["tenant_id", "type", "is_enabled"])
    op.create_index(
        "idx_strategy_trigger",
        "memory_strategy_unit",
        ["tenant_id", "trigger_intent", "trigger_stage", "trigger_objection_type", "trigger_level"],
    )

    if dialect == "postgresql":
        op.create_index(
            "idx_strategy_evidence_gin",
            "memory_strategy_unit",
            ["evidence_event_ids"],
            postgresql_using="gin",
        )

    op.create_table(
        "memory_audit",
        sa.Column("request_id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("input_digest", sa.Text(), nullable=True),
        sa.Column("route", sa.Text(), nullable=True),
        sa.Column("retrieved_ids", array_str, nullable=True),
        sa.Column("citations", json_type, nullable=True),
        sa.Column("compliance_hits", array_text, nullable=True),
        sa.Column("output_digest", sa.Text(), nullable=True),
        sa.Column("metadata", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_audit_tenant_session", "memory_audit", ["tenant_id", "session_id", "created_at"])
    if dialect == "postgresql":
        op.create_index(
            "idx_audit_citations_gin",
            "memory_audit",
            ["citations"],
            postgresql_using="gin",
        )


def downgrade() -> None:
    dialect = _dialect_name()

    if dialect == "postgresql":
        op.drop_index("idx_audit_citations_gin", table_name="memory_audit")
    op.drop_index("idx_audit_tenant_session", table_name="memory_audit")
    op.drop_table("memory_audit")

    if dialect == "postgresql":
        op.drop_index("idx_strategy_evidence_gin", table_name="memory_strategy_unit")
    op.drop_index("idx_strategy_trigger", table_name="memory_strategy_unit")
    op.drop_index("idx_strategy_type", table_name="memory_strategy_unit")
    op.drop_table("memory_strategy_unit")

    op.drop_index("idx_knowledge_effective", table_name="memory_knowledge")
    op.drop_index("idx_knowledge_lookup", table_name="memory_knowledge")
    op.drop_table("memory_knowledge")

    if dialect == "postgresql":
        op.drop_index("idx_persona_weakness_gin", table_name="memory_persona")
    op.drop_table("memory_persona")

    op.drop_index("idx_outcome_event", table_name="memory_outcome")
    op.drop_index("idx_outcome_tenant_session", table_name="memory_outcome")
    op.drop_table("memory_outcome")

    if dialect == "postgresql":
        op.drop_index("idx_event_suggest_taken_gin", table_name="memory_event")
        op.drop_index("idx_event_suggest_shown_gin", table_name="memory_event")
        op.drop_index("idx_event_compliance_gin", table_name="memory_event")
        op.drop_index("idx_event_entities_gin", table_name="memory_event")
        op.drop_index("idx_event_intent_topk_gin", table_name="memory_event")
    op.drop_index("idx_event_stage", table_name="memory_event")
    op.drop_index("idx_event_intent", table_name="memory_event")
    op.drop_index("idx_event_tenant_user_session", table_name="memory_event")
    op.drop_table("memory_event")
