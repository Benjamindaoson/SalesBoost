"""
RAG Evaluation using RAGAS Framework

This script evaluates the RAG pipeline using real test data and RAGAS metrics.

Usage:
    python tests/evaluation/rag_evaluation.py

Requirements:
    pip install ragas langchain openai datasets pandas
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# DeepSeek API key (OpenAI-compatible)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-dd153643728f4284a16b7eb40651615a")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_openai import ChatOpenAI
    from datasets import Dataset
except ImportError:
    print("❌ Missing dependencies. Please install:")
    print("   pip install ragas langchain langchain-openai openai datasets pandas")
    sys.exit(1)


def get_deepseek_llm():
    """Return a RAGAS-compatible LLM using DeepSeek's OpenAI-compatible API."""
    lc_llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.0,
    )
    return LangchainLLMWrapper(lc_llm)


def get_deepseek_embeddings():
    """Return RAGAS-compatible embeddings using local sentence-transformers (BGE-M3).

    DeepSeek does not expose an embedding endpoint, so we use the BGE-M3 model
    that is already a dependency of this project (sentence-transformers).
    """
    from langchain_community.embeddings import HuggingFaceEmbeddings
    lc_emb = HuggingFaceEmbeddings(
        model_name=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"),
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    return LangchainEmbeddingsWrapper(lc_emb)


def load_test_dataset(dataset_path="tests/evaluation/rag_test_dataset.json"):
    """Load annotated test dataset"""
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["test_cases"]


def run_rag_pipeline(question: str):
    """
    Run the real RAG pipeline on a question via EnhancedGraphRAGService.

    Requires:
      - QDRANT_URL / QDRANT_API_KEY (or local Qdrant at localhost:6333)
      - OPENAI_API_KEY  (used by RAGAS evaluator)
    Falls back to keyword search if GraphRAG is unavailable.
    """
    import asyncio
    import os

    async def _run():
        try:
            from app.infra.search.graph_rag_enhanced import get_graph_rag_service
            org_id = os.getenv("DEFAULT_ORG_ID", "default")
            svc = await get_graph_rag_service(org_id)
            results = await svc.search(
                query=question,
                top_k=5,
                enable_multi_hop=True,
            )
            if not results:
                raise ValueError("Empty results from GraphRAG")

            top = results[0]
            answer = top.get("content") or top.get("text") or str(top)
            contexts = [
                r.get("content") or r.get("text") or str(r)
                for r in results
            ]
            return {"answer": answer, "contexts": contexts}

        except Exception as e:
            print(f"  [GraphRAG fallback] {e}")
            try:
                from qdrant_client import QdrantClient
                from sentence_transformers import SentenceTransformer

                qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
                collection = os.getenv("QDRANT_COLLECTION", "sales_knowledge")
                model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

                encoder = SentenceTransformer(model_name)
                vector = encoder.encode(question).tolist()

                client = QdrantClient(url=qdrant_url,
                                      api_key=os.getenv("QDRANT_API_KEY"))
                hits = client.search(
                    collection_name=collection,
                    query_vector=vector,
                    limit=5,
                )
                if not hits:
                    raise ValueError("Qdrant returned no results")

                answer = hits[0].payload.get("content", str(hits[0].payload))
                contexts = [h.payload.get("content", str(h.payload)) for h in hits]
                return {"answer": answer, "contexts": contexts}

            except Exception as e2:
                print(f"  [Qdrant fallback] {e2}")
                return {
                    "answer": f"RAG pipeline unavailable. Question was: {question}",
                    "contexts": ["No context retrieved — check QDRANT_URL and service config."],
                }

    return asyncio.run(_run())


def prepare_ragas_dataset(test_cases):
    """Prepare dataset in RAGAS format"""
    questions = []
    ground_truths = []
    answers = []
    contexts = []

    print(f"\n🔄 Running RAG pipeline on {len(test_cases)} test cases...")

    for i, test_case in enumerate(test_cases, 1):
        print(f"  [{i}/{len(test_cases)}] Processing: {test_case['question'][:50]}...")

        # Run RAG pipeline
        result = run_rag_pipeline(test_case["question"])

        questions.append(test_case["question"])
        ground_truths.append(test_case["ground_truth_answer"])
        answers.append(result["answer"])
        contexts.append(result["contexts"])

    # Create RAGAS dataset
    dataset_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }

    return Dataset.from_dict(dataset_dict)


def evaluate_rag(dataset):
    """Evaluate RAG using RAGAS metrics backed by DeepSeek."""
    print("\n📊 Evaluating with RAGAS metrics (DeepSeek backend)...")
    print("   This may take a few minutes...")

    llm = get_deepseek_llm()
    embeddings = get_deepseek_embeddings()

    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]
    for m in metrics:
        m.llm = llm
        if hasattr(m, "embeddings"):
            m.embeddings = embeddings

    try:
        result = evaluate(
            dataset,
            metrics=metrics,
            llm=llm,
            embeddings=embeddings,
        )
        return result
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        print("\n💡 Check DEEPSEEK_API_KEY and network access to api.deepseek.com")
        return None


def save_results(results, test_cases, output_dir="tests/evaluation/reports"):
    """Save evaluation results"""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON results
    json_path = f"{output_dir}/rag_eval_{timestamp}.json"
    results_dict = {
        "timestamp": timestamp,
        "total_test_cases": len(test_cases),
        "metrics": {
            "faithfulness": float(results.get("faithfulness", 0)),
            "answer_relevancy": float(results.get("answer_relevancy", 0)),
            "context_precision": float(results.get("context_precision", 0)),
            "context_recall": float(results.get("context_recall", 0)),
        },
        "test_cases": test_cases,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_dict, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Results saved to: {json_path}")

    # Generate HTML report
    html_path = f"{output_dir}/rag_eval_{timestamp}.html"
    generate_html_report(results_dict, html_path)
    print(f"✅ HTML report saved to: {html_path}")

    return json_path, html_path


def generate_html_report(results, output_path):
    """Generate HTML report"""
    metrics = results["metrics"]

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RAG Evaluation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        .metric {{ display: inline-block; margin: 20px; padding: 20px; background: #f9f9f9; border-radius: 8px; min-width: 200px; }}
        .metric-name {{ font-size: 14px; color: #666; text-transform: uppercase; }}
        .metric-value {{ font-size: 36px; font-weight: bold; color: #4CAF50; margin: 10px 0; }}
        .metric-bar {{ height: 10px; background: #e0e0e0; border-radius: 5px; overflow: hidden; }}
        .metric-bar-fill {{ height: 100%; background: #4CAF50; transition: width 0.3s; }}
        .summary {{ background: #e8f5e9; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .warning {{ background: #fff3e0; padding: 15px; border-left: 4px solid #ff9800; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #4CAF50; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 RAG Evaluation Report</h1>
        <p><strong>Generated:</strong> {results['timestamp']}</p>
        <p><strong>Test Cases:</strong> {results['total_test_cases']}</p>

        <div class="summary">
            <h2>📊 Overall Metrics</h2>
            <div class="metric">
                <div class="metric-name">Faithfulness</div>
                <div class="metric-value">{metrics['faithfulness']:.3f}</div>
                <div class="metric-bar">
                    <div class="metric-bar-fill" style="width: {metrics['faithfulness']*100}%"></div>
                </div>
                <p style="font-size: 12px; color: #666;">答案是否基于检索上下文</p>
            </div>

            <div class="metric">
                <div class="metric-name">Answer Relevancy</div>
                <div class="metric-value">{metrics['answer_relevancy']:.3f}</div>
                <div class="metric-bar">
                    <div class="metric-bar-fill" style="width: {metrics['answer_relevancy']*100}%"></div>
                </div>
                <p style="font-size: 12px; color: #666;">答案与问题的相关性</p>
            </div>

            <div class="metric">
                <div class="metric-name">Context Precision</div>
                <div class="metric-value">{metrics['context_precision']:.3f}</div>
                <div class="metric-bar">
                    <div class="metric-bar-fill" style="width: {metrics['context_precision']*100}%"></div>
                </div>
                <p style="font-size: 12px; color: #666;">相关上下文的排序质量</p>
            </div>

            <div class="metric">
                <div class="metric-name">Context Recall</div>
                <div class="metric-value">{metrics['context_recall']:.3f}</div>
                <div class="metric-bar">
                    <div class="metric-bar-fill" style="width: {metrics['context_recall']*100}%"></div>
                </div>
                <p style="font-size: 12px; color: #666;">检索到的相关信息完整性</p>
            </div>
        </div>

        <div class="warning">
            <strong>⚠️ 重要提示：</strong> 这些是基于真实测试数据的评估结果，不是理论估算。
            如果分数低于预期，这是正常的 - 真实数据永远比虚构数据更有价值。
        </div>

        <h2>📈 Interpretation Guide</h2>
        <table>
            <tr>
                <th>Score Range</th>
                <th>Interpretation</th>
                <th>Action</th>
            </tr>
            <tr>
                <td>0.8 - 1.0</td>
                <td>Excellent</td>
                <td>System performing well</td>
            </tr>
            <tr>
                <td>0.6 - 0.8</td>
                <td>Good</td>
                <td>Minor improvements needed</td>
            </tr>
            <tr>
                <td>0.4 - 0.6</td>
                <td>Fair</td>
                <td>Significant improvements needed</td>
            </tr>
            <tr>
                <td>0.0 - 0.4</td>
                <td>Poor</td>
                <td>Major overhaul required</td>
            </tr>
        </table>

        <h2>🔧 Next Steps</h2>
        <ul>
            <li>Review low-scoring test cases to identify patterns</li>
            <li>Improve retrieval strategy (HyDE, reranking)</li>
            <li>Enhance context quality and relevance</li>
            <li>Tune generation parameters</li>
            <li>Expand test dataset for better coverage</li>
        </ul>
    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def main():
    """Main evaluation workflow"""
    print("=" * 80)
    print("RAG Evaluation with RAGAS")
    print("=" * 80)

    # Load test dataset
    print("\n📂 Loading test dataset...")
    test_cases = load_test_dataset()
    print(f"✅ Loaded {len(test_cases)} test cases")

    # Prepare RAGAS dataset
    ragas_dataset = prepare_ragas_dataset(test_cases)

    # Evaluate
    results = evaluate_rag(ragas_dataset)

    if results is None:
        print("\n❌ Evaluation failed. Please check error messages above.")
        return

    # Print results
    print("\n" + "=" * 80)
    print("📊 RAGAS Evaluation Results")
    print("=" * 80)
    print(f"Faithfulness:       {results['faithfulness']:.3f}")
    print(f"Answer Relevancy:   {results['answer_relevancy']:.3f}")
    print(f"Context Precision:  {results['context_precision']:.3f}")
    print(f"Context Recall:     {results['context_recall']:.3f}")
    print("=" * 80)

    # Save results
    json_path, html_path = save_results(results, test_cases)

    print("\n✅ Evaluation complete!")
    print(f"\n📄 View HTML report: {html_path}")
    print("\n💡 Tip: These are REAL scores based on actual testing.")
    print("   Use these numbers in your documentation instead of estimates.")


if __name__ == "__main__":
    main()
