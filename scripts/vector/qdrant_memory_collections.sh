#!/usr/bin/env bash
set -euo pipefail

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
VECTOR_SIZE="${VECTOR_SIZE:-1536}"

create_collection() {
  local name="$1"
  curl -sS -X PUT "${QDRANT_URL}/collections/${name}" \
    -H "Content-Type: application/json" \
    -d "{\"vectors\":{\"size\":${VECTOR_SIZE},\"distance\":\"Cosine\"}}"
}

create_index() {
  local name="$1"
  local field="$2"
  local schema="$3"
  curl -sS -X PUT "${QDRANT_URL}/collections/${name}/index" \
    -H "Content-Type: application/json" \
    -d "{\"field_name\":\"${field}\",\"field_schema\":\"${schema}\"}"
}

echo "Creating collections at ${QDRANT_URL} (vector size: ${VECTOR_SIZE})"

create_collection "memory_event_summary"
create_index "memory_event_summary" "tenant_id" "keyword"
create_index "memory_event_summary" "user_id" "keyword"
create_index "memory_event_summary" "session_id" "keyword"
create_index "memory_event_summary" "event_id" "keyword"
create_index "memory_event_summary" "speaker" "keyword"
create_index "memory_event_summary" "intent_top1" "keyword"
create_index "memory_event_summary" "stage" "keyword"
create_index "memory_event_summary" "objection_type" "keyword"
create_index "memory_event_summary" "entities" "keyword"
create_index "memory_event_summary" "compliance_flags" "keyword"
create_index "memory_event_summary" "created_at" "integer"

create_collection "memory_knowledge"
create_index "memory_knowledge" "tenant_id" "keyword"
create_index "memory_knowledge" "knowledge_id" "keyword"
create_index "memory_knowledge" "domain" "keyword"
create_index "memory_knowledge" "product_id" "keyword"
create_index "memory_knowledge" "version" "keyword"
create_index "memory_knowledge" "effective_from" "keyword"
create_index "memory_knowledge" "effective_to" "keyword"
create_index "memory_knowledge" "is_enabled" "bool"
create_index "memory_knowledge" "source_ref" "keyword"

create_collection "memory_strategy_unit"
create_index "memory_strategy_unit" "tenant_id" "keyword"
create_index "memory_strategy_unit" "strategy_id" "keyword"
create_index "memory_strategy_unit" "type" "keyword"
create_index "memory_strategy_unit" "trigger_intent" "keyword"
create_index "memory_strategy_unit" "trigger_stage" "keyword"
create_index "memory_strategy_unit" "trigger_objection_type" "keyword"
create_index "memory_strategy_unit" "trigger_level" "keyword"
create_index "memory_strategy_unit" "adoption_rate" "float"
create_index "memory_strategy_unit" "progress_rate" "float"
create_index "memory_strategy_unit" "risk_rate" "float"

echo "Qdrant collections ready."
