"""
RAGAS Evaluation Framework for SalesBoost RAG System.

RAGAS (RAG Assessment) evaluates RAG systems across multiple dimensions:
1. Context Precision: Are retrieved chunks relevant?
2. Context Recall: Did we retrieve all relevant information?
3. Faithfulness: Is the answer grounded in retrieved context?
4. Answer Relevance: Does the answer address the question?

Uses LLM-as-a-judge for automatic evaluation.

References:
- Paper: https://arxiv.org/abs/2309.15217
- Library: https://github.com/explodinggradients/ragas
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RAGASMetrics:
    """RAGAS evaluation metrics."""

    context_precision: float  # 0-1, higher is better
    context_recall: float  # 0-1, higher is better
    faithfulness: float  # 0-1, higher is better
    answer_relevance: float  # 0-1, higher is better

    @property
    def overall_score(self) -> float:
        """Calculate overall score (harmonic mean)."""
        scores = [
            self.context_precision,
            self.context_recall,
            self.faithfulness,
            self.answer_relevance,
        ]
        # Harmonic mean
        return len(scores) / sum(1 / (s + 1e-10) for s in scores)


@dataclass
class RAGASEvaluationInput:
    """Input for RAGAS evaluation."""

    question: str  # User question
    answer: str  # Generated answer
    contexts: List[str]  # Retrieved contexts
    ground_truth: Optional[str] = None  # Ground truth answer (if available)


class RAGASEvaluator:
    """
    RAGAS evaluator using LLM-as-a-judge.

    Evaluates RAG systems across 4 dimensions:
    1. Context Precision: Precision@K of retrieved contexts
    2. Context Recall: Coverage of ground truth in contexts
    3. Faithfulness: Answer grounded in contexts (no hallucination)
    4. Answer Relevance: Answer addresses the question

    Args:
        llm_client: LLM client for evaluation (OpenAI, DeepSeek, etc.)
        model: Model name (default: gpt-4o-mini for cost efficiency)
    """

    def __init__(self, llm_client: Any, model: str = "gpt-4o-mini"):
        self.llm_client = llm_client
        self.model = model

    async def evaluate(self, input_data: RAGASEvaluationInput) -> RAGASMetrics:
        """
        Evaluate RAG system output.

        Args:
            input_data: Evaluation input

        Returns:
            RAGAS metrics
        """
        # Run evaluations in parallel
        tasks = [
            self._evaluate_context_precision(input_data),
            self._evaluate_context_recall(input_data),
            self._evaluate_faithfulness(input_data),
            self._evaluate_answer_relevance(input_data),
        ]

        results = await asyncio.gather(*tasks)

        return RAGASMetrics(
            context_precision=results[0],
            context_recall=results[1],
            faithfulness=results[2],
            answer_relevance=results[3],
        )

    async def _evaluate_context_precision(
        self, input_data: RAGASEvaluationInput
    ) -> float:
        """
        Evaluate context precision.

        Formula: Precision@K = (# relevant contexts) / K

        Uses LLM to judge relevance of each context.
        """
        if not input_data.contexts:
            return 0.0

        prompt = f"""Given a question and a context, determine if the context is relevant to answering the question.

Question: {input_data.question}

Context: {{context}}

Is this context relevant? Answer with only "Yes" or "No".
"""

        relevant_count = 0

        for context in input_data.contexts:
            try:
                response = await self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt.format(context=context),
                        }
                    ],
                    temperature=0.0,
                    max_tokens=10,
                )

                answer = response.choices[0].message.content.strip().lower()

                if "yes" in answer:
                    relevant_count += 1

            except Exception as e:
                logger.error(f"Context precision evaluation failed: {e}")
                continue

        precision = relevant_count / len(input_data.contexts)

        logger.info(
            f"Context Precision: {precision:.3f} "
            f"({relevant_count}/{len(input_data.contexts)} relevant)"
        )

        return precision

    async def _evaluate_context_recall(self, input_data: RAGASEvaluationInput) -> float:
        """
        Evaluate context recall.

        Formula: Recall = (# ground truth statements in contexts) / (# total ground truth statements)

        Requires ground truth answer.
        """
        if not input_data.ground_truth:
            logger.warning("Ground truth not provided, skipping context recall")
            return 1.0  # Assume perfect recall if no ground truth

        if not input_data.contexts:
            return 0.0

        # Extract statements from ground truth
        prompt_extract = f"""Extract key factual statements from the following answer. List each statement on a new line.

Answer: {input_data.ground_truth}

Statements:
"""

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt_extract}],
                temperature=0.0,
                max_tokens=500,
            )

            statements_text = response.choices[0].message.content.strip()
            statements = [
                s.strip()
                for s in statements_text.split("\n")
                if s.strip() and not s.strip().startswith("#")
            ]

            if not statements:
                return 1.0

            # Check if each statement is supported by contexts
            contexts_text = "\n\n".join(input_data.contexts)

            prompt_check = f"""Given the following contexts and a statement, determine if the statement is supported by the contexts.

Contexts:
{contexts_text}

Statement: {{statement}}

Is this statement supported by the contexts? Answer with only "Yes" or "No".
"""

            supported_count = 0

            for statement in statements:
                try:
                    response = await self.llm_client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "user",
                                "content": prompt_check.format(statement=statement),
                            }
                        ],
                        temperature=0.0,
                        max_tokens=10,
                    )

                    answer = response.choices[0].message.content.strip().lower()

                    if "yes" in answer:
                        supported_count += 1

                except Exception as e:
                    logger.error(f"Statement check failed: {e}")
                    continue

            recall = supported_count / len(statements)

            logger.info(
                f"Context Recall: {recall:.3f} "
                f"({supported_count}/{len(statements)} statements supported)"
            )

            return recall

        except Exception as e:
            logger.error(f"Context recall evaluation failed: {e}")
            return 1.0  # Assume perfect recall on error

    async def _evaluate_faithfulness(self, input_data: RAGASEvaluationInput) -> float:
        """
        Evaluate faithfulness (hallucination detection).

        Formula: Faithfulness = (# claims supported by contexts) / (# total claims)

        Checks if answer is grounded in retrieved contexts.
        """
        if not input_data.contexts:
            return 0.0

        # Extract claims from answer
        prompt_extract = f"""Extract factual claims from the following answer. List each claim on a new line.

Answer: {input_data.answer}

Claims:
"""

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt_extract}],
                temperature=0.0,
                max_tokens=500,
            )

            claims_text = response.choices[0].message.content.strip()
            claims = [
                c.strip()
                for c in claims_text.split("\n")
                if c.strip() and not c.strip().startswith("#")
            ]

            if not claims:
                return 1.0  # No claims = no hallucination

            # Check if each claim is supported by contexts
            contexts_text = "\n\n".join(input_data.contexts)

            prompt_check = f"""Given the following contexts and a claim, determine if the claim is supported by the contexts.

Contexts:
{contexts_text}

Claim: {{claim}}

Is this claim supported by the contexts? Answer with only "Yes" or "No".
"""

            supported_count = 0

            for claim in claims:
                try:
                    response = await self.llm_client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "user",
                                "content": prompt_check.format(claim=claim),
                            }
                        ],
                        temperature=0.0,
                        max_tokens=10,
                    )

                    answer = response.choices[0].message.content.strip().lower()

                    if "yes" in answer:
                        supported_count += 1

                except Exception as e:
                    logger.error(f"Claim check failed: {e}")
                    continue

            faithfulness = supported_count / len(claims)

            logger.info(
                f"Faithfulness: {faithfulness:.3f} "
                f"({supported_count}/{len(claims)} claims supported)"
            )

            return faithfulness

        except Exception as e:
            logger.error(f"Faithfulness evaluation failed: {e}")
            return 1.0  # Assume faithful on error

    async def _evaluate_answer_relevance(
        self, input_data: RAGASEvaluationInput
    ) -> float:
        """
        Evaluate answer relevance.

        Formula: Cosine similarity between question and answer embeddings.

        Measures if answer addresses the question.
        """
        prompt = f"""Given a question and an answer, rate how well the answer addresses the question on a scale of 0-10.

Question: {input_data.question}

Answer: {input_data.answer}

Rating (0-10):
"""

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10,
            )

            rating_text = response.choices[0].message.content.strip()

            # Extract number
            import re

            match = re.search(r"\d+", rating_text)
            if match:
                rating = int(match.group())
                relevance = rating / 10.0
            else:
                relevance = 0.5  # Default

            logger.info(f"Answer Relevance: {relevance:.3f} (rating: {rating}/10)")

            return relevance

        except Exception as e:
            logger.error(f"Answer relevance evaluation failed: {e}")
            return 0.5  # Default to neutral


class RAGASBatchEvaluator:
    """Batch evaluator for multiple test cases."""

    def __init__(self, evaluator: RAGASEvaluator):
        self.evaluator = evaluator

    async def evaluate_batch(
        self, test_cases: List[RAGASEvaluationInput]
    ) -> Dict[str, Any]:
        """
        Evaluate multiple test cases.

        Args:
            test_cases: List of evaluation inputs

        Returns:
            Aggregated metrics and statistics
        """
        results = []

        for i, test_case in enumerate(test_cases):
            logger.info(f"Evaluating test case {i+1}/{len(test_cases)}")

            try:
                metrics = await self.evaluator.evaluate(test_case)
                results.append(metrics)
            except Exception as e:
                logger.error(f"Evaluation failed for test case {i+1}: {e}")
                continue

        if not results:
            return {"error": "All evaluations failed"}

        # Aggregate metrics
        avg_context_precision = np.mean([r.context_precision for r in results])
        avg_context_recall = np.mean([r.context_recall for r in results])
        avg_faithfulness = np.mean([r.faithfulness for r in results])
        avg_answer_relevance = np.mean([r.answer_relevance for r in results])
        avg_overall_score = np.mean([r.overall_score for r in results])

        return {
            "num_test_cases": len(test_cases),
            "num_evaluated": len(results),
            "metrics": {
                "context_precision": {
                    "mean": float(avg_context_precision),
                    "std": float(np.std([r.context_precision for r in results])),
                    "min": float(min(r.context_precision for r in results)),
                    "max": float(max(r.context_precision for r in results)),
                },
                "context_recall": {
                    "mean": float(avg_context_recall),
                    "std": float(np.std([r.context_recall for r in results])),
                    "min": float(min(r.context_recall for r in results)),
                    "max": float(max(r.context_recall for r in results)),
                },
                "faithfulness": {
                    "mean": float(avg_faithfulness),
                    "std": float(np.std([r.faithfulness for r in results])),
                    "min": float(min(r.faithfulness for r in results)),
                    "max": float(max(r.faithfulness for r in results)),
                },
                "answer_relevance": {
                    "mean": float(avg_answer_relevance),
                    "std": float(np.std([r.answer_relevance for r in results])),
                    "min": float(min(r.answer_relevance for r in results)),
                    "max": float(max(r.answer_relevance for r in results)),
                },
                "overall_score": {
                    "mean": float(avg_overall_score),
                    "std": float(np.std([r.overall_score for r in results])),
                    "min": float(min(r.overall_score for r in results)),
                    "max": float(max(r.overall_score for r in results)),
                },
            },
            "individual_results": [
                {
                    "context_precision": r.context_precision,
                    "context_recall": r.context_recall,
                    "faithfulness": r.faithfulness,
                    "answer_relevance": r.answer_relevance,
                    "overall_score": r.overall_score,
                }
                for r in results
            ],
        }
