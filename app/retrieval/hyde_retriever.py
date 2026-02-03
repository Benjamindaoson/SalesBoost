"""
HyDE (Hypothetical Document Embeddings) for SalesBoost RAG.

HyDE improves retrieval by:
1. User asks a question
2. LLM generates a "hypothetical ideal answer"
3. Use the hypothetical answer to search (not the question)
4. Retrieve real documents similar to the hypothetical answer

Why it works:
- Questions and answers live in different semantic spaces
- Hypothetical answers are closer to real answers in embedding space
- Dramatically improves recall for vague/unclear questions

References:
- Paper: https://arxiv.org/abs/2212.10496
- "Precise Zero-Shot Dense Retrieval without Relevance Labels"
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HyDEResult:
    """HyDE retrieval result."""

    query: str  # Original query
    hypothetical_document: str  # Generated hypothetical answer
    retrieved_documents: List[Dict[str, Any]]  # Retrieved real documents
    metadata: Dict[str, Any]  # Additional metadata


class HyDEGenerator:
    """
    Generates hypothetical documents for improved retrieval.

    Strategy:
    1. Generate multiple hypothetical answers (diversity)
    2. Embed each hypothetical answer
    3. Retrieve using each embedding
    4. Aggregate and deduplicate results
    """

    def __init__(
        self,
        llm_client: Any,
        model: str = "gpt-4o-mini",
        num_hypothetical_docs: int = 1,
    ):
        """
        Initialize HyDE generator.

        Args:
            llm_client: LLM client for generation
            model: Model name
            num_hypothetical_docs: Number of hypothetical docs to generate
        """
        self.llm_client = llm_client
        self.model = model
        self.num_hypothetical_docs = num_hypothetical_docs

    async def generate_hypothetical_document(
        self,
        query: str,
        domain: str = "sales",
        language: str = "zh",
    ) -> str:
        """
        Generate a hypothetical document that would answer the query.

        Args:
            query: User query
            domain: Domain context (sales, legal, medical, etc.)
            language: Language (zh, en)

        Returns:
            Hypothetical document text
        """
        # Domain-specific prompts
        domain_prompts = {
            "sales": {
                "zh": """你是一位资深销售专家。请根据以下问题，生成一个理想的、详细的销售话术或解决方案。

问题：{query}

请直接给出答案，不要说"我会..."或"可以..."，而是直接写出具体的销售话术或方案。

理想答案：""",
                "en": """You are a senior sales expert. Based on the following question, generate an ideal, detailed sales script or solution.

Question: {query}

Provide the answer directly without saying "I would..." or "You can...", but write the specific sales script or solution directly.

Ideal Answer:""",
            },
            "general": {
                "zh": """请根据以下问题，生成一个理想的、详细的答案。

问题：{query}

理想答案：""",
                "en": """Based on the following question, generate an ideal, detailed answer.

Question: {query}

Ideal Answer:""",
            },
        }

        # Select prompt
        prompt_template = domain_prompts.get(domain, domain_prompts["general"]).get(
            language, domain_prompts["general"]["zh"]
        )

        prompt = prompt_template.format(query=query)

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Some creativity
                max_tokens=500,
            )

            hypothetical_doc = response.choices[0].message.content.strip()

            logger.info(
                f"Generated hypothetical document for query: {query[:50]}... "
                f"(length: {len(hypothetical_doc)} chars)"
            )

            return hypothetical_doc

        except Exception as e:
            logger.error(f"Hypothetical document generation failed: {e}")
            # Fallback: return the query itself
            return query

    async def generate_multiple_hypothetical_documents(
        self,
        query: str,
        domain: str = "sales",
        language: str = "zh",
    ) -> List[str]:
        """
        Generate multiple diverse hypothetical documents.

        Args:
            query: User query
            domain: Domain context
            language: Language

        Returns:
            List of hypothetical documents
        """
        if self.num_hypothetical_docs == 1:
            doc = await self.generate_hypothetical_document(query, domain, language)
            return [doc]

        # Generate multiple with different temperatures for diversity
        import asyncio

        tasks = []

        for i in range(self.num_hypothetical_docs):
            # Vary temperature for diversity
            temperature = 0.5 + (i * 0.2)

            task = self._generate_with_temperature(
                query, domain, language, temperature
            )
            tasks.append(task)

        hypothetical_docs = await asyncio.gather(*tasks)

        return hypothetical_docs

    async def _generate_with_temperature(
        self,
        query: str,
        domain: str,
        language: str,
        temperature: float,
    ) -> str:
        """Generate with specific temperature."""
        domain_prompts = {
            "sales": {
                "zh": """你是一位资深销售专家。请根据以下问题，生成一个理想的、详细的销售话术或解决方案。

问题：{query}

理想答案：""",
            },
            "general": {
                "zh": """请根据以下问题，生成一个理想的、详细的答案。

问题：{query}

理想答案：""",
            },
        }

        prompt_template = domain_prompts.get(domain, domain_prompts["general"]).get(
            language, domain_prompts["general"]["zh"]
        )

        prompt = prompt_template.format(query=query)

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return query


class HyDERetriever:
    """
    HyDE-enhanced retriever.

    Workflow:
    1. Generate hypothetical document(s)
    2. Embed hypothetical document(s)
    3. Retrieve using hypothetical embeddings
    4. Aggregate and deduplicate results
    5. Return top-k
    """

    def __init__(
        self,
        hyde_generator: HyDEGenerator,
        vector_store: Any,
        num_hypothetical_docs: int = 1,
        aggregation_method: str = "rrf",  # "rrf" or "max_score"
    ):
        """
        Initialize HyDE retriever.

        Args:
            hyde_generator: HyDE generator instance
            vector_store: Vector store for retrieval
            num_hypothetical_docs: Number of hypothetical docs to use
            aggregation_method: How to aggregate results ("rrf" or "max_score")
        """
        self.hyde_generator = hyde_generator
        self.vector_store = vector_store
        self.num_hypothetical_docs = num_hypothetical_docs
        self.aggregation_method = aggregation_method

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        domain: str = "sales",
        language: str = "zh",
        filters: Optional[Dict[str, Any]] = None,
    ) -> HyDEResult:
        """
        Retrieve using HyDE.

        Args:
            query: User query
            top_k: Number of results to return
            domain: Domain context
            language: Language
            filters: Optional filters

        Returns:
            HyDE result with retrieved documents
        """
        # Step 1: Generate hypothetical document(s)
        if self.num_hypothetical_docs == 1:
            hypothetical_docs = [
                await self.hyde_generator.generate_hypothetical_document(
                    query, domain, language
                )
            ]
        else:
            hypothetical_docs = (
                await self.hyde_generator.generate_multiple_hypothetical_documents(
                    query, domain, language
                )
            )

        # Step 2: Retrieve using each hypothetical document
        all_results = []

        for i, hyp_doc in enumerate(hypothetical_docs):
            try:
                # Use hypothetical document as query
                results = await self.vector_store.search(
                    query=hyp_doc,
                    top_k=top_k * 2,  # Retrieve more for aggregation
                    filters=filters,
                )

                # Tag with source
                for result in results:
                    result["hyde_source"] = i

                all_results.extend(results)

            except Exception as e:
                logger.error(f"Retrieval failed for hypothetical doc {i}: {e}")
                continue

        # Step 3: Aggregate results
        if self.aggregation_method == "rrf":
            final_results = self._aggregate_rrf(all_results, top_k)
        else:
            final_results = self._aggregate_max_score(all_results, top_k)

        return HyDEResult(
            query=query,
            hypothetical_document=hypothetical_docs[0],  # Return first one
            retrieved_documents=final_results,
            metadata={
                "num_hypothetical_docs": len(hypothetical_docs),
                "aggregation_method": self.aggregation_method,
                "total_retrieved": len(all_results),
            },
        )

    def _aggregate_rrf(
        self, results: List[Dict[str, Any]], top_k: int, k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Aggregate using RRF (Reciprocal Rank Fusion).

        Formula: score = sum(1 / (k + rank))
        """
        # Group by document ID
        doc_scores = {}
        doc_map = {}

        # Group results by hyde_source
        results_by_source = {}
        for result in results:
            source = result.get("hyde_source", 0)
            if source not in results_by_source:
                results_by_source[source] = []
            results_by_source[source].append(result)

        # Calculate RRF scores
        for source, source_results in results_by_source.items():
            for rank, result in enumerate(source_results):
                doc_id = result.get("id")
                if not doc_id:
                    continue

                if doc_id not in doc_scores:
                    doc_scores[doc_id] = 0.0
                    doc_map[doc_id] = result

                # RRF score
                doc_scores[doc_id] += 1.0 / (k + rank + 1)

        # Sort by score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        # Return top-k
        final_results = []
        for doc_id, score in sorted_docs[:top_k]:
            doc = doc_map[doc_id].copy()
            doc["score"] = score
            final_results.append(doc)

        return final_results

    def _aggregate_max_score(
        self, results: List[Dict[str, Any]], top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Aggregate by taking maximum score for each document.
        """
        # Group by document ID
        doc_map = {}

        for result in results:
            doc_id = result.get("id")
            if not doc_id:
                continue

            score = result.get("score", 0.0)

            if doc_id not in doc_map or score > doc_map[doc_id]["score"]:
                doc_map[doc_id] = result

        # Sort by score
        sorted_docs = sorted(
            doc_map.values(), key=lambda x: x.get("score", 0.0), reverse=True
        )

        return sorted_docs[:top_k]
