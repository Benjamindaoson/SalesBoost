# SalesBoost Data Ingestion

## 1. Overview
The Data Ingestion Pipeline has been upgraded to **L5 Production Grade**.
It ensures **Deterministic**, **Stable**, and **Semantic** chunking without relying on LLMs in the critical path.

## 2. Key Features

### ✅ Deterministic Ingestion (Mandatory)
- **No LLM in Main Loop**: All semantic tagging is rule-based (Regex/Keyword) via `taxonomy.py`.
- **Structural Chunking**: Respects Markdown Headers, Tables, Lists, Code Blocks, and FAQs.
- **Stable IDs**: IDs are generated from `source_id + doc_sha256 + section_path + index`. Re-running ingestion on the same file produces identical IDs.

### 🏷️ Semantic Metadata
- **Taxonomy**: Explicitly defined in `app/services/ingestion/taxonomy.py`.
- **Types**: `pricing`, `feature`, `comparison`, `faq`, `procedure`, `objection_handling`, `code`.
- **Governance**: `semantic_schema_version` is embedded in every chunk.

### ⚡ Performance
- **Async-Free**: Core chunking is synchronous CPU-bound logic, easy to scale.
- **Vector Integration**: Metadata is fully searchable in Vector DB.

## 3. Usage

### Run Ingestion
```bash
python scripts/run_ingestion.py --dir "path/to/documents"
```

### Run Tests
```bash
python tests/ingestion/test_chunking_v2.py
```
(Integration test is inside `test_integration.py` but can be run similarly)

## 4. Architecture

1.  **Loader**: Reads PDF/Docx/Txt -> `Document`
2.  **SemanticChunker**:
    *   **Structural Parsing**: Markdown/Regex state machine.
    *   **Tagging**: `classify_text` (Rule-based).
    *   **Splitting**: Recursive Token Limit (Hard limit).
    *   **ID Gen**: Stable Hashing.
3.  **Vector Store**: Stores `content` + `metadata` (including `semantic_type`).

## 5. Verification Checklist
- [x] Main loop has NO LLM calls.
- [x] Chunk IDs are stable across runs.
- [x] Semantic types are populated based on rules.
- [x] Tables and Lists are kept intact (unless exceeding hard token limit).
