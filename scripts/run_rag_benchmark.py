#!/usr/bin/env python3
"""
One-click RAG benchmark runner.

Steps:
  1. Start Qdrant via Docker (if not already running)
  2. Ingest data/processed/semantic_chunks_optimized.json into Qdrant
  3. Run RAGAS evaluation with DeepSeek LLM + BGE-M3 embeddings
  4. Print results and save report to tests/evaluation/reports/

Usage:
    python scripts/run_rag_benchmark.py

Requirements:
    docker (in PATH)
    pip install qdrant-client sentence-transformers ragas langchain langchain-openai langchain-community datasets
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CHUNKS_FILE  = PROJECT_ROOT / "data" / "processed" / "semantic_chunks_optimized.json"
TEST_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "rag_test_dataset.json"
REPORTS_DIR  = PROJECT_ROOT / "tests" / "evaluation" / "reports"

# Qdrant
QDRANT_URL        = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY    = os.getenv("QDRANT_API_KEY", "")
COLLECTION_NAME   = os.getenv("QDRANT_COLLECTION", "sales_knowledge")
EMBEDDING_MODEL   = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
VECTOR_DIM        = 1024  # BGE-M3

# DeepSeek
DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY", "sk-dd153643728f4284a16b7eb40651615a")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL    = "deepseek-chat"


# ---------------------------------------------------------------------------
# Step 1: Ensure Qdrant is running
# ---------------------------------------------------------------------------
def ensure_qdrant():
    import urllib.request
    import urllib.error

    def _is_up():
        try:
            urllib.request.urlopen(f"{QDRANT_URL}/healthz", timeout=3)
            return True
        except Exception:
            return False

    if _is_up():
        print("[Qdrant] Already running at", QDRANT_URL)
        return

    print("[Qdrant] Not detected — starting via Docker...")
    try:
        subprocess.run(
            [
                "docker", "run", "-d", "--name", "qdrant-benchmark",
                "-p", "6333:6333", "-p", "6334:6334",
                "qdrant/qdrant",
            ],
            check=True,
            capture_output=True,
        )
        print("[Qdrant] Container started, waiting for readiness...")
        for _ in range(30):
            time.sleep(1)
            if _is_up():
                print("[Qdrant] Ready.")
                return
        raise RuntimeError("Qdrant did not become ready in 30s")
    except FileNotFoundError:
        print("[ERROR] Docker not found. Start Qdrant manually:")
        print("        docker run -p 6333:6333 qdrant/qdrant")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        if "already in use" in stderr or "Conflict" in stderr:
            # Container exists but stopped — restart it
            subprocess.run(["docker", "start", "qdrant-benchmark"], check=True)
            print("[Qdrant] Restarted existing container, waiting...")
            for _ in range(30):
                time.sleep(1)
                if _is_up():
                    print("[Qdrant] Ready.")
                    return
        raise


# ---------------------------------------------------------------------------
# Step 2: Ingest chunks
# ---------------------------------------------------------------------------
def ingest_chunks():
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from sentence_transformers import SentenceTransformer

    print("\n[Ingest] Loading chunks from", CHUNKS_FILE)
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"[Ingest] {len(chunks)} chunks loaded")

    kwargs = {"url": QDRANT_URL}
    if QDRANT_API_KEY:
        kwargs["api_key"] = QDRANT_API_KEY
    client = QdrantClient(**kwargs)

    # Check if already ingested
    collections = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME in collections:
        info = client.get_collection(COLLECTION_NAME)
        if (info.points_count or 0) >= len(chunks):
            print(f"[Ingest] Collection '{COLLECTION_NAME}' already has {info.points_count} points — skipping ingest.")
            return
        print(f"[Ingest] Collection exists but only {info.points_count} points — re-ingesting.")
        client.delete_collection(COLLECTION_NAME)

    print(f"[Ingest] Creating collection '{COLLECTION_NAME}' (dim={VECTOR_DIM}, cosine)")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )

    print(f"[Ingest] Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    BATCH = 32
    ingested = 0
    for i in range(0, len(chunks), BATCH):
        batch  = chunks[i : i + BATCH]
        texts  = [c["text"] for c in batch]
        vecs   = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        points = [
            PointStruct(
                id=abs(hash(c["id"])) % (10 ** 9),
                vector=vecs[j].tolist(),
                payload={
                    "content": c["text"],      # unified key used by RAG pipeline
                    "text":    c["text"],
                    "source":  c.get("source", ""),
                    "type":    c.get("type", ""),
                    "metadata": c.get("metadata", {}),
                },
            )
            for j, c in enumerate(batch)
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        ingested += len(batch)
        print(f"[Ingest] {ingested}/{len(chunks)} chunks uploaded", end="\r")

    print(f"\n[Ingest] Done — {ingested} chunks in '{COLLECTION_NAME}'")


# ---------------------------------------------------------------------------
# Step 3: Query helper used by RAGAS
# ---------------------------------------------------------------------------
def qdrant_search(question: str, top_k: int = 5):
    from qdrant_client import QdrantClient
    from sentence_transformers import SentenceTransformer

    kwargs = {"url": QDRANT_URL}
    if QDRANT_API_KEY:
        kwargs["api_key"] = QDRANT_API_KEY
    client = QdrantClient(**kwargs)
    model  = SentenceTransformer(EMBEDDING_MODEL)
    vector = model.encode(question, normalize_embeddings=True).tolist()
    hits   = client.search(collection_name=COLLECTION_NAME, query_vector=vector, limit=top_k)
    return hits


# ---------------------------------------------------------------------------
# Step 4: RAGAS evaluation
# ---------------------------------------------------------------------------
def run_ragas():
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from langchain_openai import ChatOpenAI
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from datasets import Dataset
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("  pip install ragas langchain langchain-openai langchain-community datasets")
        sys.exit(1)

    # Load test cases
    print("\n[RAGAS] Loading test dataset from", TEST_DATASET)
    with open(TEST_DATASET, "r", encoding="utf-8") as f:
        test_cases = json.load(f)["test_cases"]
    print(f"[RAGAS] {len(test_cases)} test cases")

    # Build RAGAS dataset by querying Qdrant for each question
    questions, answers, contexts, ground_truths = [], [], [], []
    print("[RAGAS] Running retrieval for each question...")
    for i, tc in enumerate(test_cases, 1):
        q = tc["question"]
        print(f"  [{i}/{len(test_cases)}] {q[:60]}")
        hits = qdrant_search(q)
        top_answer = hits[0].payload.get("content", "") if hits else "No result"
        ctx = [h.payload.get("content", "") for h in hits]
        questions.append(q)
        answers.append(top_answer)
        contexts.append(ctx)
        ground_truths.append(tc["ground_truth_answer"])

    dataset = Dataset.from_dict({
        "question":     questions,
        "answer":       answers,
        "contexts":     contexts,
        "ground_truth": ground_truths,
    })

    # LLM: DeepSeek
    llm = LangchainLLMWrapper(
        ChatOpenAI(
            model=DEEPSEEK_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.0,
        )
    )

    # Embeddings: local BGE-M3
    embeddings = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    )

    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    for m in metrics:
        m.llm = llm
        if hasattr(m, "embeddings"):
            m.embeddings = embeddings

    print("\n[RAGAS] Evaluating (this calls DeepSeek API)...")
    result = evaluate(dataset, metrics=metrics, llm=llm, embeddings=embeddings)

    scores = {
        "faithfulness":      float(result["faithfulness"]),
        "answer_relevancy":  float(result["answer_relevancy"]),
        "context_precision": float(result["context_precision"]),
        "context_recall":    float(result["context_recall"]),
    }

    # Print
    print("\n" + "=" * 60)
    print("RAGAS Results (DeepSeek + BGE-M3, Qdrant backend)")
    print("=" * 60)
    for k, v in scores.items():
        bar = "#" * int(v * 20)
        print(f"  {k:<22} {v:.3f}  [{bar:<20}]")
    print("=" * 60)

    # Save JSON report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"ragas_{ts}.json"
    report = {
        "timestamp": ts,
        "llm": DEEPSEEK_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "collection": COLLECTION_NAME,
        "n_test_cases": len(test_cases),
        "scores": scores,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[RAGAS] Report saved: {report_path}")
    return scores


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("SalesBoost RAG Benchmark")
    print("=" * 60)

    ensure_qdrant()
    ingest_chunks()
    run_ragas()
