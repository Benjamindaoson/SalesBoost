# SalesBoost System Upgrade Plan: RAG & Frontend Evolution

Based on the analysis of your data (`D:\SalesBoost\销冠能力复制数据库`) and current system architecture, here is the comprehensive upgrade plan to transform SalesBoost into a Multi-Modal, Expert-Driven training platform.

## 1. RAG System Upgrade (Backend)
**Goal:** Enable the system to "hear" sales recordings, "read" Excel comparisons, and "understand" SOPs.

### A. Multi-Modal Data Ingestion Pipeline
We will upgrade `DocumentProcessor` to handle the specific file types in your dataset:
1.  **Audio Ingestion (.mp3/.wav)**:
    -   **Action**: Integrate `openai-whisper` or API-based transcription.
    -   **Feature**: Implement "Speaker Diarization" to distinguish between "Sales Rep" and "Customer".
    -   **Output**: Transcribed text + Timestamped metadata (to allow playback later).
2.  **Structured Data Ingestion (.xlsx)**:
    -   **Action**: Use `pandas` to parse "Competitor Analysis" (Safari vs Platinum).
    -   **Feature**: Convert rows into "Semantic Triples" or JSON blobs for precise retrieval (e.g., `{"card": "Safari", "feature": "Golf", "value": "Unlimited"}`).
    -   **Benefit**: Allows the Coach to answer specific questions like "How does our annual fee compare?" accurately.
3.  **SOP Extraction (.docx/.pdf)**:
    -   **Action**: Use `LangChain` or custom parsing to extract "Rules" and "Scripts" from the SOP documents.
    -   **Output**: Automatically generate `ComplianceRule` entries (e.g., "Do not promise 100% returns") from the SOPs.

### B. Knowledge Graph (GraphRAG)
**Goal**: Connect scattered knowledge points (e.g., "Objection A" -> "Script B" -> "Audio Example C").
1.  **Implementation**: Build a lightweight graph structure linking:
    -   `SalesStage` (e.g., Objection Handling)
    -   `Topic` (e.g., Annual Fee)
    -   `Evidence` (Link to Excel row or Audio snippet)

## 2. Frontend Interaction Upgrade (Frontend)
**Goal**: Make the AI's advice verifiable and actionable.

### A. "Evidence-Based" Coaching UI
Modify `training_room.html` to display citations:
1.  **Citation Cards**: When the Coach gives advice, show a clickable "Source" badge.
    -   *Example*: "Source: Competitor Analysis_v2.xlsx (Row 14)"
2.  **Audio Playback Widget**:
    -   If the RAG retrieves a "Sales Champion Recording", display a mini-player: `[▶ Play Expert Example (02:14)]`.
    -   Allow the user to hear *exactly* how the champion handled that objection.

### B. Rich Media Response
1.  **Data Tables**: If the user asks for a comparison, render a mini HTML table (extracted from Excel) instead of just text.

## 3. Multi-Agent Module Updates
1.  **Coach Agent**:
    -   **Upgrade**: Add `tool_use` capability to query the `KnowledgeService` with specific filters (e.g., `type="competitor_data"`).
2.  **Compliance Agent**:
    -   **Upgrade**: Auto-load rules extracted from the "Sales SOP" folder.

## 4. Implementation Steps
1.  **Dependency Update**: Add `pandas`, `openpyxl`, `openai-whisper` (or API client).
2.  **Ingestion Script**: Create `scripts/ingest_champion_data.py` to batch process the folder.
3.  **Backend Logic**: Update `KnowledgeService` to store and retrieve "Rich Metadata" (timestamps, file paths).
4.  **Frontend Logic**: Update WebSocket handler to render `citation` and `audio` objects.

**Ready to execute?** I will start by creating the ingestion script to process your Excel and Audio files.