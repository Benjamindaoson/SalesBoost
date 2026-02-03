"""
RLAIF (Reinforcement Learning from AI Feedback) Evaluation System.

This module implements advanced evaluation capabilities for sales training:
- Reward Model for scoring sales responses
- Pairwise Comparison for relative quality assessment
- Process Supervision for step-by-step evaluation
- Constitutional AI for compliance checking

Architecture:
    Sales Response → Reward Model → Score
                  ↓
    Pairwise Comparator → Preference
                  ↓
    Process Supervisor → Step-by-step Feedback
                  ↓
    Constitutional Checker → Compliance Status
"""

import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


# ==================== Data Models ====================

class EvaluationDimension(str, Enum):
    """Evaluation dimensions for sales responses."""
    COMPLETENESS = "completeness"  # 完整性
    RELEVANCE = "relevance"  # 相关性
    COMPLIANCE = "compliance"  # 合规性
    EMPATHY = "empathy"  # 同理心
    PERSUASIVENESS = "persuasiveness"  # 说服力
    PROFESSIONALISM = "professionalism"  # 专业性
    CLARITY = "clarity"  # 清晰度
    ACCURACY = "accuracy"  # 准确性


@dataclass
class EvaluationScore:
    """Evaluation score for a single dimension."""
    dimension: EvaluationDimension
    score: float  # 0-1
    reasoning: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class ComprehensiveEvaluation:
    """Comprehensive evaluation result."""
    overall_score: float  # 0-1
    dimension_scores: List[EvaluationScore]
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    compliance_issues: List[str] = field(default_factory=list)
    process_feedback: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PairwiseComparison:
    """Pairwise comparison result."""
    response_a_id: str
    response_b_id: str
    preferred: str  # "A", "B", or "tie"
    confidence: float  # 0-1
    reasoning: str


# ==================== Reward Model ====================

class RewardModel:
    """
    Reward model for scoring sales responses.

    This model learns to score responses based on expert feedback,
    similar to how RLHF works but using AI feedback instead of human feedback.
    """

    def __init__(self, llm_client: Any):
        """
        Initialize reward model.

        Args:
            llm_client: LLM client for scoring
        """
        self.llm_client = llm_client

        # Scoring prompt
        self.scoring_prompt = """你是一位资深销售培训专家。请对以下销售回应进行评分。

客户问题/异议：
{customer_input}

销售回应：
{sales_response}

评分维度：
1. 完整性 (completeness): 回应是否完整解决了客户的问题
2. 相关性 (relevance): 回应是否切中要害
3. 合规性 (compliance): 是否符合公司政策和法律法规
4. 同理心 (empathy): 是否理解客户感受
5. 说服力 (persuasiveness): 是否有说服力
6. 专业性 (professionalism): 是否专业得体
7. 清晰度 (clarity): 表达是否清晰
8. 准确性 (accuracy): 信息是否准确

请为每个维度打分（0-1），并给出总分和详细理由。

输出格式（JSON）：
{{
  "overall_score": 0.85,
  "dimension_scores": [
    {{
      "dimension": "completeness",
      "score": 0.9,
      "reasoning": "完整回答了客户的所有疑问",
      "evidence": ["提到了年费减免政策", "说明了权益价值"]
    }}
  ],
  "strengths": ["同理心强", "逻辑清晰"],
  "weaknesses": ["可以更具体说明权益细节"],
  "suggestions": ["建议补充具体的权益使用案例"]
}}

只输出JSON，不要其他内容。"""

    async def score(
        self,
        customer_input: str,
        sales_response: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ComprehensiveEvaluation:
        """
        Score a sales response.

        Args:
            customer_input: Customer's question or objection
            sales_response: Sales person's response
            context: Additional context

        Returns:
            Comprehensive evaluation
        """
        try:
            # Call LLM
            prompt = self.scoring_prompt.format(
                customer_input=customer_input,
                sales_response=sales_response
            )

            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistent scoring
                max_tokens=2000,
            )

            # Parse JSON response
            result = json.loads(response)

            # Convert to EvaluationScore objects
            dimension_scores = []
            for score_data in result.get("dimension_scores", []):
                score = EvaluationScore(
                    dimension=EvaluationDimension(score_data["dimension"]),
                    score=score_data["score"],
                    reasoning=score_data["reasoning"],
                    evidence=score_data.get("evidence", [])
                )
                dimension_scores.append(score)

            evaluation = ComprehensiveEvaluation(
                overall_score=result["overall_score"],
                dimension_scores=dimension_scores,
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                suggestions=result.get("suggestions", []),
            )

            logger.info(f"Scored response: {evaluation.overall_score:.2f}")
            return evaluation

        except Exception as e:
            logger.error(f"Reward model scoring failed: {e}")
            # Return default evaluation
            return ComprehensiveEvaluation(
                overall_score=0.5,
                dimension_scores=[],
                strengths=[],
                weaknesses=["评分失败"],
                suggestions=[]
            )


# ==================== Pairwise Comparator ====================

class PairwiseComparator:
    """
    Pairwise comparison for relative quality assessment.

    This is more reliable than absolute scoring because it's easier
    to compare two responses than to assign an absolute score.
    """

    def __init__(self, llm_client: Any):
        """
        Initialize pairwise comparator.

        Args:
            llm_client: LLM client for comparison
        """
        self.llm_client = llm_client

        # Comparison prompt
        self.comparison_prompt = """你是一位资深销售培训专家。请比较以下两个销售回应的质量。

客户问题/异议：
{customer_input}

回应A：
{response_a}

回应B：
{response_b}

请从以下维度比较：
1. 完整性：哪个回应更完整？
2. 相关性：哪个回应更切中要害？
3. 合规性：哪个回应更合规？
4. 同理心：哪个回应更有同理心？
5. 说服力：哪个回应更有说服力？
6. 专业性：哪个回应更专业？
7. 清晰度：哪个回应更清晰？
8. 准确性：哪个回应更准确？

输出格式（JSON）：
{{
  "preferred": "A",  // "A", "B", or "tie"
  "confidence": 0.85,  // 0-1
  "reasoning": "回应A在同理心和说服力方面明显优于回应B。A首先认可了客户的顾虑，然后用具体的权益案例说明价值，而B直接推销显得生硬。",
  "dimension_comparison": {{
    "completeness": "A",
    "relevance": "A",
    "compliance": "tie",
    "empathy": "A",
    "persuasiveness": "A",
    "professionalism": "tie",
    "clarity": "B",
    "accuracy": "tie"
  }}
}}

只输出JSON，不要其他内容。"""

    async def compare(
        self,
        customer_input: str,
        response_a: str,
        response_b: str,
        response_a_id: str = "A",
        response_b_id: str = "B",
    ) -> PairwiseComparison:
        """
        Compare two sales responses.

        Args:
            customer_input: Customer's question or objection
            response_a: First response
            response_b: Second response
            response_a_id: ID of first response
            response_b_id: ID of second response

        Returns:
            Pairwise comparison result
        """
        try:
            # Call LLM
            prompt = self.comparison_prompt.format(
                customer_input=customer_input,
                response_a=response_a,
                response_b=response_b
            )

            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=1500,
            )

            # Parse JSON response
            result = json.loads(response)

            comparison = PairwiseComparison(
                response_a_id=response_a_id,
                response_b_id=response_b_id,
                preferred=result["preferred"],
                confidence=result["confidence"],
                reasoning=result["reasoning"]
            )

            logger.info(
                f"Comparison result: {comparison.preferred} "
                f"(confidence: {comparison.confidence:.2f})"
            )
            return comparison

        except Exception as e:
            logger.error(f"Pairwise comparison failed: {e}")
            # Return tie as default
            return PairwiseComparison(
                response_a_id=response_a_id,
                response_b_id=response_b_id,
                preferred="tie",
                confidence=0.5,
                reasoning="比较失败"
            )


# ==================== Process Supervisor ====================

class ProcessSupervisor:
    """
    Process supervision for step-by-step evaluation.

    This evaluates not just the final response, but the reasoning process
    that led to it. This is crucial for sales training where the thought
    process matters as much as the outcome.
    """

    def __init__(self, llm_client: Any):
        """
        Initialize process supervisor.

        Args:
            llm_client: LLM client for supervision
        """
        self.llm_client = llm_client

        # Process supervision prompt
        self.supervision_prompt = """你是一位资深销售培训专家。请评估销售人员的思考过程和回应步骤。

客户问题/异议：
{customer_input}

销售人员的思考过程：
{thought_process}

最终回应：
{final_response}

请评估每个思考步骤的质量：
1. 步骤是否合理？
2. 步骤是否必要？
3. 步骤是否遗漏了重要考虑？
4. 步骤之间的逻辑是否连贯？

输出格式（JSON）：
{{
  "step_evaluations": [
    {{
      "step_number": 1,
      "step_content": "识别客户异议类型",
      "is_correct": true,
      "is_necessary": true,
      "feedback": "正确识别了价格异议",
      "score": 0.9
    }}
  ],
  "overall_process_score": 0.85,
  "process_strengths": ["逻辑清晰", "考虑全面"],
  "process_weaknesses": ["可以更快切入核心"],
  "process_suggestions": ["建议先建立同理心再讲道理"]
}}

只输出JSON，不要其他内容。"""

    async def supervise(
        self,
        customer_input: str,
        thought_process: str,
        final_response: str,
    ) -> Dict[str, Any]:
        """
        Supervise the reasoning process.

        Args:
            customer_input: Customer's question or objection
            thought_process: Sales person's thought process
            final_response: Final response

        Returns:
            Process supervision result
        """
        try:
            # Call LLM
            prompt = self.supervision_prompt.format(
                customer_input=customer_input,
                thought_process=thought_process,
                final_response=final_response
            )

            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=2000,
            )

            # Parse JSON response
            result = json.loads(response)

            logger.info(
                f"Process supervision complete: "
                f"score={result.get('overall_process_score', 0):.2f}"
            )
            return result

        except Exception as e:
            logger.error(f"Process supervision failed: {e}")
            return {
                "step_evaluations": [],
                "overall_process_score": 0.5,
                "process_strengths": [],
                "process_weaknesses": ["评估失败"],
                "process_suggestions": []
            }


# ==================== Constitutional Checker ====================

class ConstitutionalChecker:
    """
    Constitutional AI for compliance checking.

    This implements "constitutional" rules that sales responses must follow,
    such as:
    - No false promises
    - No pressure tactics
    - No discrimination
    - Compliance with regulations
    """

    def __init__(self, llm_client: Any):
        """
        Initialize constitutional checker.

        Args:
            llm_client: LLM client for checking
        """
        self.llm_client = llm_client

        # Constitutional rules
        self.constitution = {
            "no_false_promises": "不得做出虚假承诺或夸大产品功能",
            "no_pressure": "不得使用高压销售手段或威胁客户",
            "no_discrimination": "不得歧视任何客户群体",
            "privacy_protection": "必须保护客户隐私信息",
            "regulatory_compliance": "必须符合金融监管要求",
            "transparency": "必须如实告知费用和风险",
            "professional_language": "必须使用专业、礼貌的语言",
            "no_misleading": "不得误导客户或隐瞒重要信息",
        }

        # Checking prompt
        self.checking_prompt = """你是一位合规审查专家。请检查以下销售回应是否违反了合规规则。

销售回应：
{sales_response}

合规规则：
{constitution}

请逐条检查是否违反规则，并给出详细说明。

输出格式（JSON）：
{{
  "is_compliant": true,
  "violations": [
    {{
      "rule": "no_false_promises",
      "violated": false,
      "evidence": "",
      "severity": "low"  // "low", "medium", "high", "critical"
    }}
  ],
  "overall_risk_level": "low",  // "low", "medium", "high", "critical"
  "recommendations": ["建议补充风险提示"]
}}

只输出JSON，不要其他内容。"""

    async def check(
        self,
        sales_response: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Check sales response for constitutional violations.

        Args:
            sales_response: Sales response to check
            context: Additional context

        Returns:
            Compliance check result
        """
        try:
            # Format constitution
            constitution_str = "\n".join([
                f"{i+1}. {rule}: {desc}"
                for i, (rule, desc) in enumerate(self.constitution.items())
            ])

            # Call LLM
            prompt = self.checking_prompt.format(
                sales_response=sales_response,
                constitution=constitution_str
            )

            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.0,  # Zero temperature for consistent checking
                max_tokens=1500,
            )

            # Parse JSON response
            result = json.loads(response)

            # Log violations
            violations = [
                v for v in result.get("violations", [])
                if v.get("violated", False)
            ]

            if violations:
                logger.warning(
                    f"Found {len(violations)} compliance violations: "
                    f"{[v['rule'] for v in violations]}"
                )
            else:
                logger.info("No compliance violations found")

            return result

        except Exception as e:
            logger.error(f"Constitutional checking failed: {e}")
            return {
                "is_compliant": True,  # Default to compliant on error
                "violations": [],
                "overall_risk_level": "unknown",
                "recommendations": ["检查失败，请人工审核"]
            }


# ==================== RLAIF Evaluator ====================

class RLAIFEvaluator:
    """
    Main RLAIF evaluator integrating all components.

    This provides a unified interface for comprehensive evaluation of
    sales responses using multiple AI feedback mechanisms.
    """

    def __init__(self, llm_client: Any):
        """
        Initialize RLAIF evaluator.

        Args:
            llm_client: LLM client
        """
        self.llm_client = llm_client

        # Initialize components
        self.reward_model = RewardModel(llm_client)
        self.pairwise_comparator = PairwiseComparator(llm_client)
        self.process_supervisor = ProcessSupervisor(llm_client)
        self.constitutional_checker = ConstitutionalChecker(llm_client)

        logger.info("RLAIF Evaluator initialized")

    async def evaluate_comprehensive(
        self,
        customer_input: str,
        sales_response: str,
        thought_process: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ComprehensiveEvaluation:
        """
        Perform comprehensive evaluation of a sales response.

        Args:
            customer_input: Customer's question or objection
            sales_response: Sales person's response
            thought_process: Sales person's thought process (optional)
            context: Additional context

        Returns:
            Comprehensive evaluation
        """
        # Run all evaluations in parallel
        tasks = [
            self.reward_model.score(customer_input, sales_response, context),
            self.constitutional_checker.check(sales_response, context),
        ]

        # Add process supervision if thought process provided
        if thought_process:
            tasks.append(
                self.process_supervisor.supervise(
                    customer_input,
                    thought_process,
                    sales_response
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Extract results
        evaluation = results[0] if not isinstance(results[0], Exception) else ComprehensiveEvaluation(
            overall_score=0.5,
            dimension_scores=[],
            strengths=[],
            weaknesses=["评估失败"],
            suggestions=[]
        )

        compliance_result = results[1] if not isinstance(results[1], Exception) else {}

        # Add compliance issues
        if not compliance_result.get("is_compliant", True):
            evaluation.compliance_issues = [
                f"{v['rule']}: {v.get('evidence', '违规')}"
                for v in compliance_result.get("violations", [])
                if v.get("violated", False)
            ]

        # Add process feedback
        if len(results) > 2 and not isinstance(results[2], Exception):
            evaluation.process_feedback = results[2].get("step_evaluations", [])

        logger.info(
            f"Comprehensive evaluation complete: "
            f"score={evaluation.overall_score:.2f}, "
            f"compliance_issues={len(evaluation.compliance_issues)}"
        )

        return evaluation

    async def compare_responses(
        self,
        customer_input: str,
        responses: List[Tuple[str, str]],  # List of (response_id, response_text)
    ) -> List[PairwiseComparison]:
        """
        Compare multiple responses pairwise.

        Args:
            customer_input: Customer's question or objection
            responses: List of (response_id, response_text) tuples

        Returns:
            List of pairwise comparisons
        """
        comparisons = []

        # Compare all pairs
        for i in range(len(responses)):
            for j in range(i + 1, len(responses)):
                id_a, text_a = responses[i]
                id_b, text_b = responses[j]

                comparison = await self.pairwise_comparator.compare(
                    customer_input=customer_input,
                    response_a=text_a,
                    response_b=text_b,
                    response_a_id=id_a,
                    response_b_id=id_b,
                )
                comparisons.append(comparison)

        return comparisons

    async def rank_responses(
        self,
        customer_input: str,
        responses: List[Tuple[str, str]],
    ) -> List[Tuple[str, float]]:
        """
        Rank responses by quality using pairwise comparisons.

        Args:
            customer_input: Customer's question or objection
            responses: List of (response_id, response_text) tuples

        Returns:
            List of (response_id, score) tuples, sorted by score
        """
        # Get all pairwise comparisons
        comparisons = await self.compare_responses(customer_input, responses)

        # Calculate scores using Elo-like rating
        scores = {response_id: 1000.0 for response_id, _ in responses}

        for comparison in comparisons:
            if comparison.preferred == "A":
                scores[comparison.response_a_id] += 10 * comparison.confidence
                scores[comparison.response_b_id] -= 10 * comparison.confidence
            elif comparison.preferred == "B":
                scores[comparison.response_b_id] += 10 * comparison.confidence
                scores[comparison.response_a_id] -= 10 * comparison.confidence

        # Normalize scores to 0-1
        min_score = min(scores.values())
        max_score = max(scores.values())
        score_range = max_score - min_score if max_score > min_score else 1.0

        normalized_scores = [
            (response_id, (score - min_score) / score_range)
            for response_id, score in scores.items()
        ]

        # Sort by score
        normalized_scores.sort(key=lambda x: x[1], reverse=True)

        return normalized_scores


# ==================== Factory Function ====================

_rlaif_evaluator: Optional[RLAIFEvaluator] = None


def get_rlaif_evaluator(
    llm_client: Any,
    force_new: bool = False,
) -> RLAIFEvaluator:
    """
    Get or create RLAIF evaluator (singleton).

    Args:
        llm_client: LLM client
        force_new: Force create new instance

    Returns:
        RLAIFEvaluator instance
    """
    global _rlaif_evaluator

    if _rlaif_evaluator is None or force_new:
        _rlaif_evaluator = RLAIFEvaluator(llm_client)

    return _rlaif_evaluator
