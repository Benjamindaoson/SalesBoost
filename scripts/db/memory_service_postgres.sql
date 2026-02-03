-- Memory Service PostgreSQL DDL (production)
-- Aligns with docs/api/memory_service_api.md and memory_service_models.py

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS memory_event (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    channel TEXT,
    turn_index INTEGER,
    speaker TEXT NOT NULL CHECK (speaker IN ('sales','customer','npc','agent')),
    raw_text_ref TEXT,
    summary TEXT,
    intent_top1 TEXT,
    intent_topk TEXT[],
    stage TEXT,
    objection_type TEXT,
    entities TEXT[],
    sentiment TEXT,
    tension NUMERIC(4,3),
    compliance_flags TEXT[],
    coach_suggestions_shown TEXT[],
    coach_suggestions_taken TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_tenant_user_session
    ON memory_event (tenant_id, user_id, session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_event_intent
    ON memory_event (tenant_id, intent_top1);
CREATE INDEX IF NOT EXISTS idx_event_stage
    ON memory_event (tenant_id, stage);
CREATE INDEX IF NOT EXISTS idx_event_intent_topk_gin
    ON memory_event USING GIN (intent_topk);
CREATE INDEX IF NOT EXISTS idx_event_entities_gin
    ON memory_event USING GIN (entities);
CREATE INDEX IF NOT EXISTS idx_event_compliance_gin
    ON memory_event USING GIN (compliance_flags);
CREATE INDEX IF NOT EXISTS idx_event_suggest_shown_gin
    ON memory_event USING GIN (coach_suggestions_shown);
CREATE INDEX IF NOT EXISTS idx_event_suggest_taken_gin
    ON memory_event USING GIN (coach_suggestions_taken);

CREATE TABLE IF NOT EXISTS memory_outcome (
    outcome_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    event_id TEXT NOT NULL REFERENCES memory_event(event_id),
    adopted BOOLEAN NOT NULL,
    adopt_type TEXT CHECK (adopt_type IN ('script','action_list')),
    stage_before TEXT,
    stage_after TEXT,
    eval_scores JSONB DEFAULT '{}'::jsonb,
    compliance_result TEXT CHECK (compliance_result IN ('pass','blocked')),
    final_result TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outcome_tenant_session
    ON memory_outcome (tenant_id, session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_event
    ON memory_outcome (tenant_id, event_id);

CREATE TABLE IF NOT EXISTS memory_persona (
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    level TEXT,
    weakness_tags TEXT[],
    last_eval_summary TEXT,
    last_improvements TEXT[],
    next_actions TEXT[],
    history_stats JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (tenant_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_persona_weakness_gin
    ON memory_persona USING GIN (weakness_tags);

CREATE TABLE IF NOT EXISTS memory_knowledge (
    tenant_id TEXT NOT NULL,
    knowledge_id TEXT NOT NULL,
    domain TEXT NOT NULL CHECK (domain IN ('权益','活动','佣金','合规')),
    product_id TEXT,
    structured_content JSONB NOT NULL,
    source_ref TEXT,
    version TEXT NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_enabled BOOLEAN DEFAULT TRUE,
    citation_snippets TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (tenant_id, knowledge_id, version)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_lookup
    ON memory_knowledge (tenant_id, domain, product_id, is_enabled);
CREATE INDEX IF NOT EXISTS idx_knowledge_effective
    ON memory_knowledge (tenant_id, effective_from, effective_to);

CREATE TABLE IF NOT EXISTS memory_strategy_unit (
    tenant_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('SOP','异议','推进','合规替代')),
    trigger_intent TEXT,
    trigger_stage TEXT,
    trigger_objection_type TEXT,
    trigger_level TEXT,
    trigger_condition JSONB DEFAULT '{}'::jsonb,
    steps TEXT[],
    scripts TEXT[],
    dos_donts JSONB DEFAULT '{}'::jsonb,
    evidence_event_ids TEXT[],
    stats JSONB DEFAULT '{}'::jsonb,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (tenant_id, strategy_id)
);

CREATE INDEX IF NOT EXISTS idx_strategy_type
    ON memory_strategy_unit (tenant_id, type, is_enabled);
CREATE INDEX IF NOT EXISTS idx_strategy_trigger
    ON memory_strategy_unit (tenant_id, trigger_intent, trigger_stage, trigger_objection_type, trigger_level);
CREATE INDEX IF NOT EXISTS idx_strategy_evidence_gin
    ON memory_strategy_unit USING GIN (evidence_event_ids);

CREATE TABLE IF NOT EXISTS memory_audit (
    request_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT,
    session_id TEXT,
    input_digest TEXT,
    route TEXT,
    retrieved_ids TEXT[],
    citations JSONB DEFAULT '[]'::jsonb,
    compliance_hits TEXT[],
    output_digest TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant_session
    ON memory_audit (tenant_id, session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_citations_gin
    ON memory_audit USING GIN (citations);
