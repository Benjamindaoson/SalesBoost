"""
Self-RAG (Self-Reflective Retrieval-Augmented Generation) for SalesBoost.

Self-RAG adds reflection and self-correction to RAG:
1. Retrieve documents
2. Generate answer
3. Self-reflect: Is the answer good? Are sources relevant?
4. If not good → Refine query and retrieve again
5. Repeat until satisfied or max iterations

Key components:
- Relevance Checker: Are retrieved docs relevant?
- Faithfulness Checker: Is answer grounded in docs?
- Answer Quality Checker: Is answer complete and accurate?

References:
- Paper: https://arxiv.org/abs/2310.11511
- "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection"
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Tuple

logger = logging.getLogger(__name__)


class ReflectionDecision(str, Enum):
    """Reflection decision types."""

    ACCEPT = "accept"  # Answer is good, stop
    REFINE_QUERY = "refine_query"  # Query needs refinement
    RETRIEVE_MORE = "retrieve_more"  # Need more context
    REGENERATE = "regenerate"  # Answer needs regeneration


@dataclass
class ReflectionResult:
    """Result of self-reflection."""

    decision: ReflectionDecision
    reasoning: str
    relevance_score: float  # 0-1
    faithfulness_score: float  # 0-1
    completeness_score: float  # 0-1
    suggestions: List[str]  # Suggestions for improvement


@dataclass
class SelfRAGResult:
    """Final result from Self-RAG."""

    query: str
    answer: str
    contexts: List[str]
    iterations: int
    reflection_history: List[ReflectionResult]
    final_quality_score: float


class ReflectionAgent:
    """
    Agent that reflects on RAG outputs and decides next actions.

    Uses LLM to evaluate:
    1. Relevance: Are retrieved docs relevant to query?
    2. Faithfulness: Is answer grounded in docs?
    3. Completeness: Does answer fully address query?
    """

    def __init__(self, llm_client: Any, model: str = "gpt-4o-mini"):
        self.llm_client = llm_client
        self.model = model

    async def reflect(
        self,
        query: str,
        answer: str,
        contexts: List[str],
    ) -> ReflectionResult:
        """
        Reflect on RAG output and decide next action.

        Args:
            query: User query
            answer: Generated answer
            contexts: Retrieved contexts

        Returns:
            Reflection result with decision
        """
        # Evaluate in parallel
        import asyncio

        tasks = [
            self._check_relevance(query, contexts),
            self._check_faithfulness(answer, contexts),
            self._check_completeness(query, answer),
        ]

        results = await asyncio.gather(*tasks)

        relevance_score = results[0]
        faithfulness_score = results[1]
        completeness_score = results[2]

        # Decision logic
        decision, reasoning, suggestions = self._make_decision(
            relevance_score, faithfulness_score, completeness_score
        )

        return ReflectionResult(
            decision=decision,
            reasoning=reasoning,
            relevance_score=relevance_score,
            faithfulness_score=faithfulness_score,
            completeness_score=completeness_score,
            suggestions=suggestions,
        )

    async def _check_relevance(self, query: str, contexts: List[str]) -> float:
        """Check if retrieved contexts are relevant to query."""
        if not contexts:
            return 0.0

        contexts_text = "\n\n".join(contexts[:3])  # Check first 3 only

        prompt = f"""Rate the relevance of the following contexts to the query on a scale of 0-10.

Query: {query}

Contexts:
{contexts_text}

Are these contexts relevant to answering the query?

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

            import re

            match = re.search(r"\d+", rating_text)
            if match:
                rating = int(match.group())
                return rating / 10.0
            else:
                return 0.5

        except Exception as e:
            logger.error(f"Relevance check failed: {e}")
            return 0.5

    async def _check_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """Check if answer is grounded in contexts (no hallucination)."""
        if not contexts:
            return 0.0

        contexts_text = "\n\n".join(contexts)

        prompt = f"""Rate how well the answer is supported by the contexts on a scale of 0-10.

Contexts:
{contexts_text}

Answer: {answer}

Is the answer fully grounded in the contexts without hallucination?

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

            import re

            match = re.search(r"\d+", rating_text)
            if match:
                rating = int(match.group())
                return rating / 10.0
            else:
                return 0.5

        except Exception as e:
            logger.error(f"Faithfulness check failed: {e}")
            return 0.5

    async def _check_completeness(self, query: str, answer: str) -> float:
        """Check if answer completely addresses the query."""
        prompt = f"""Rate how completely the answer addresses the query on a scale of 0-10.

Query: {query}

Answer: {answer}

Does the answer fully and completely address all aspects of the query?

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

            import re

            match = re.search(r"\d+", rating_text)
            if match:
                rating = int(match.group())
                return rating / 10.0
            else:
                return 0.5

        except Exception as e:
            logger.error(f"Completeness check failed: {e}")
            return 0.5

    def _make_decision(
        self,
        relevance_score: float,
        faithfulness_score: float,
        completeness_score: float,
    ) -> Tuple[ReflectionDecision, str, List[str]]:
        """
        Make decision based on scores.

        Decision logic:
        - All scores > 0.7 → ACCEPT
        - Relevance < 0.5 → REFINE_QUERY
        - Faithfulness < 0.5 → RETRIEVE_MORE
        - Completeness < 0.5 → REGENERATE
        """
        suggestions = []

        # Check if all good
        if (
            relevance_score >= 0.7
            and faithfulness_score >= 0.7
            and completeness_score >= 0.7
        ):
            return (
                ReflectionDecision.ACCEPT,
                "All quality metrics are satisfactory",
                [],
            )

        # Prioritize issues
        if relevance_score < 0.5:
            suggestions.append("Retrieved documents are not relevant to the query")
            suggestions.append("Consider refining the query to be more specific")
            return (
                ReflectionDecision.REFINE_QUERY,
                f"Low relevance score ({relevance_score:.2f})",
                suggestions,
            )

        if faithfulness_score < 0.5:
            suggestions.append("Answer contains information not in the contexts")
            suggestions.append("Need to retrieve more relevant documents")
            return (
                ReflectionDecision.RETRIEVE_MORE,
                f"Low faithfulness score ({faithfulness_score:.2f})",
                suggestions,
            )

        if completeness_score < 0.5:
            suggestions.append("Answer does not fully address the query")
            suggestions.append("Regenerate answer with more detail")
            return (
                ReflectionDecision.REGENERATE,
                f"Low completeness score ({completeness_score:.2f})",
                suggestions,
            )

        # Moderate scores - try to improve
        if relevance_score < 0.7:
            return (
                ReflectionDecision.REFINE_QUERY,
                f"Moderate relevance score ({relevance_score:.2f})",
                ["Query could be more specific"],
            )

        if faithfulness_score < 0.7:
            return (
                ReflectionDecision.RETRIEVE_MORE,
                f"Moderate faithfulness score ({faithfulness_score:.2f})",
                ["Could benefit from more context"],
            )

        # Default: regenerate
        return (
            ReflectionDecision.REGENERATE,
            f"Moderate completeness score ({completeness_score:.2f})",
            ["Answer could be more complete"],
        )


class SelfRAGEngine:
    """
    Self-RAG engine with reflection loop.

    Workflow:
    1. Retrieve documents
    2. Generate answer
    3. Reflect on quality
    4. If not satisfied → Take action (refine/retrieve/regenerate)
    5. Repeat until satisfied or max iterations
    """

    def __init__(
        self,
        retriever: Any,
        generator: Any,
        reflection_agent: ReflectionAgent,
        max_iterations: int = 3,
        quality_threshold: float = 0.7,
    ):
        """
        Initialize Self-RAG engine.

        Args:
            retriever: Retriever instance
            generator: Generator (LLM) instance
            reflection_agent: Reflection agent
            max_iterations: Maximum reflection iterations
            quality_threshold: Minimum quality score to accept
        """
        self.retriever = retriever
        self.generator = generator
        self.reflection_agent = reflection_agent
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold

    async def generate_with_reflection(
        self,
        query: str,
        top_k: int = 5,
    ) -> SelfRAGResult:
        """
        Generate answer with self-reflection loop.

        Args:
            query: User query
            top_k: Number of documents to retrieve

        Returns:
            Self-RAG result with final answer
        """
        current_query = query
        reflection_history = []
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1

            logger.info(f"Self-RAG iteration {iteration}/{self.max_iterations}")

            # Step 1: Retrieve
            try:
                retrieval_results = await self.retriever.search(
                    query=current_query, top_k=top_k
                )

                contexts = [r.content for r in retrieval_results]

            except Exception as e:
                logger.error(f"Retrieval failed: {e}")
                contexts = []

            if not contexts:
                logger.warning("No contexts retrieved, stopping")
                break

            # Step 2: Generate
            try:
                answer = await self._generate_answer(current_query, contexts)
            except Exception as e:
                logger.error(f"Generation failed: {e}")
                answer = "抱歉，我无法生成答案。"

            # Step 3: Reflect
            reflection = await self.reflection_agent.reflect(
                query=current_query, answer=answer, contexts=contexts
            )

            reflection_history.append(reflection)

            logger.info(
                f"Reflection: {reflection.decision} "
                f"(relevance={reflection.relevance_score:.2f}, "
                f"faithfulness={reflection.faithfulness_score:.2f}, "
                f"completeness={reflection.completeness_score:.2f})"
            )

            # Step 4: Decide next action
            if reflection.decision == ReflectionDecision.ACCEPT:
                logger.info("Answer accepted, stopping")
                break

            elif reflection.decision == ReflectionDecision.REFINE_QUERY:
                # Refine query
                current_query = await self._refine_query(query, reflection)
                logger.info(f"Refined query: {current_query}")

            elif reflection.decision == ReflectionDecision.RETRIEVE_MORE:
                # Increase top_k
                top_k = min(top_k * 2, 20)
                logger.info(f"Retrieving more documents (top_k={top_k})")

            elif reflection.decision == ReflectionDecision.REGENERATE:
                # Regenerate with same contexts
                logger.info("Regenerating answer")
                # Will regenerate in next iteration

        # Calculate final quality score
        if reflection_history:
            last_reflection = reflection_history[-1]
            final_quality_score = (
                last_reflection.relevance_score
                + last_reflection.faithfulness_score
                + last_reflection.completeness_score
            ) / 3.0
        else:
            final_quality_score = 0.0

        return SelfRAGResult(
            query=query,
            answer=answer,
            contexts=contexts,
            iterations=iteration,
            reflection_history=reflection_history,
            final_quality_score=final_quality_score,
        )

    async def _generate_answer(self, query: str, contexts: List[str]) -> str:
        """Generate answer from contexts."""
        contexts_text = "\n\n".join(contexts)

        prompt = f"""根据以下上下文回答问题。

上下文：
{contexts_text}

问题：{query}

答案："""

        try:
            response = await self.generator.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return "抱歉，我无法生成答案。"

    async def _refine_query(
        self, original_query: str, reflection: ReflectionResult
    ) -> str:
        """Refine query based on reflection."""
        prompt = f"""原始问题不够具体，需要改进。

原始问题：{original_query}

问题：{', '.join(reflection.suggestions)}

请将原始问题改写得更具体、更明确，以便检索到更相关的文档。

改进后的问题："""

        try:
            response = await self.generator.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=100,
            )

            refined_query = response.choices[0].message.content.strip()

            return refined_query

        except Exception as e:
            logger.error(f"Query refinement failed: {e}")
            return original_query  # Fallback to original
