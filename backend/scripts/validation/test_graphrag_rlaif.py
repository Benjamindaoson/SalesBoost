"""
Test suite for Enhanced GraphRAG and RLAIF Evaluator.

This script demonstrates the usage and validates the functionality of:
1. Enhanced GraphRAG with LLM-based extraction and multi-hop reasoning
2. RLAIF Evaluation System with comprehensive feedback

Usage:
    python scripts/test_graphrag_rlaif.py
"""

import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== Mock LLM Client ====================

class MockLLMClient:
    """Mock LLM client for testing."""

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generate mock response based on prompt type."""

        # Entity extraction
        if "提取关键实体" in prompt or "extract entities" in prompt.lower():
            return """{
  "entities": [
    {
      "name": "年费太贵",
      "type": "objection",
      "properties": {
        "description": "客户对年费价格的异议",
        "context": "客户认为1000元年费过高"
      }
    },
    {
      "name": "消费达标免年费",
      "type": "response",
      "properties": {
        "description": "通过消费达标可以免除年费",
        "context": "年消费满10万即可免年费"
      }
    },
    {
      "name": "机场贵宾厅",
      "type": "benefit",
      "properties": {
        "description": "机场贵宾厅权益",
        "context": "可享受全球机场贵宾厅服务"
      }
    },
    {
      "name": "积分返现",
      "type": "benefit",
      "properties": {
        "description": "消费积分返现",
        "context": "消费可获得积分并返现"
      }
    },
    {
      "name": "价值转化",
      "type": "technique",
      "properties": {
        "description": "将价格转化为价值的销售技巧",
        "context": "强调权益价值超过年费"
      }
    }
  ]
}"""

        # Relation extraction
        elif "识别实体之间的关系" in prompt or "extract relations" in prompt.lower():
            return """{
  "relations": [
    {
      "source": "年费太贵",
      "target": "消费达标免年费",
      "type": "addresses",
      "properties": {
        "confidence": 0.95,
        "evidence": "用消费达标免年费来应对年费异议"
      }
    },
    {
      "source": "消费达标免年费",
      "target": "机场贵宾厅",
      "type": "provides_benefit",
      "properties": {
        "confidence": 0.90,
        "evidence": "免年费后可享受机场贵宾厅权益"
      }
    },
    {
      "source": "消费达标免年费",
      "target": "积分返现",
      "type": "provides_benefit",
      "properties": {
        "confidence": 0.90,
        "evidence": "免年费后可享受积分返现"
      }
    },
    {
      "source": "消费达标免年费",
      "target": "价值转化",
      "type": "part_of",
      "properties": {
        "confidence": 0.85,
        "evidence": "这是价值转化技巧的一部分"
      }
    }
  ]
}"""

        # Reward model scoring
        elif "对以下销售回应进行评分" in prompt:
            return """{
  "overall_score": 0.85,
  "dimension_scores": [
    {
      "dimension": "completeness",
      "score": 0.90,
      "reasoning": "完整回答了客户的所有疑问，包括年费、权益和价值",
      "evidence": ["提到了年费减免政策", "说明了权益价值", "给出了具体数字"]
    },
    {
      "dimension": "relevance",
      "score": 0.88,
      "reasoning": "回应切中要害，直接解决了客户的价格顾虑",
      "evidence": ["针对年费问题", "提供了解决方案"]
    },
    {
      "dimension": "compliance",
      "score": 0.95,
      "reasoning": "符合合规要求，如实告知了费用和权益",
      "evidence": ["明确说明了年费金额", "准确描述了权益内容"]
    },
    {
      "dimension": "empathy",
      "score": 0.92,
      "reasoning": "首先表达了理解，建立了同理心",
      "evidence": ["我理解您的顾虑"]
    },
    {
      "dimension": "persuasiveness",
      "score": 0.85,
      "reasoning": "用具体数据和权益说明价值，有说服力",
      "evidence": ["年消费满10万", "价值超过5000元"]
    },
    {
      "dimension": "professionalism",
      "score": 0.88,
      "reasoning": "表达专业得体，没有过度推销",
      "evidence": ["语气温和", "逻辑清晰"]
    },
    {
      "dimension": "clarity",
      "score": 0.90,
      "reasoning": "表达清晰，易于理解",
      "evidence": ["结构清晰", "用词准确"]
    },
    {
      "dimension": "accuracy",
      "score": 0.95,
      "reasoning": "信息准确，数据真实",
      "evidence": ["年费1000元", "消费满10万免年费"]
    }
  ],
  "strengths": ["同理心强", "逻辑清晰", "数据支撑", "价值转化到位"],
  "weaknesses": ["可以更具体说明权益细节", "可以补充成功案例"],
  "suggestions": ["建议补充具体的权益使用案例", "可以分享其他客户的成功经验"]
}"""

        # Pairwise comparison
        elif "比较以下两个销售回应" in prompt:
            return """{
  "preferred": "B",
  "confidence": 0.85,
  "reasoning": "回应B在同理心和说服力方面明显优于回应A。B首先认可了客户的顾虑，然后用具体的权益案例说明价值，逻辑清晰且有说服力。而A虽然也提到了免年费，但直接推销显得生硬，缺乏同理心的建立。",
  "dimension_comparison": {
    "completeness": "B",
    "relevance": "tie",
    "compliance": "tie",
    "empathy": "B",
    "persuasiveness": "B",
    "professionalism": "B",
    "clarity": "tie",
    "accuracy": "tie"
  }
}"""

        # Process supervision
        elif "评估销售人员的思考过程" in prompt:
            return """{
  "step_evaluations": [
    {
      "step_number": 1,
      "step_content": "识别异议类型：价格异议",
      "is_correct": true,
      "is_necessary": true,
      "feedback": "正确识别了客户的价格异议，这是应对的基础",
      "score": 0.95
    },
    {
      "step_number": 2,
      "step_content": "建立同理心：认可客户顾虑",
      "is_correct": true,
      "is_necessary": true,
      "feedback": "建立同理心是关键步骤，有助于降低客户防御心理",
      "score": 0.90
    },
    {
      "step_number": 3,
      "step_content": "价值转化：说明权益价值",
      "is_correct": true,
      "is_necessary": true,
      "feedback": "价值转化是核心技巧，将价格转化为价值",
      "score": 0.92
    },
    {
      "step_number": 4,
      "step_content": "提供解决方案：消费达标免年费",
      "is_correct": true,
      "is_necessary": true,
      "feedback": "提供具体解决方案，给客户明确的行动路径",
      "score": 0.88
    }
  ],
  "overall_process_score": 0.91,
  "process_strengths": ["逻辑清晰", "考虑全面", "步骤完整"],
  "process_weaknesses": ["可以更快切入核心", "可以补充数据支撑"],
  "process_suggestions": ["建议在步骤2和3之间增加需求确认", "可以在步骤4后增加促成环节"]
}"""

        # Constitutional checking
        elif "检查以下销售回应是否违反了合规规则" in prompt:
            if "必须今天办理" in prompt:
                return """{
  "is_compliant": false,
  "violations": [
    {
      "rule": "no_pressure",
      "violated": true,
      "evidence": "使用了'必须今天办理，否则明天就涨价'等高压话术",
      "severity": "high"
    },
    {
      "rule": "no_false_promises",
      "violated": false,
      "evidence": "",
      "severity": "low"
    },
    {
      "rule": "transparency",
      "violated": false,
      "evidence": "",
      "severity": "low"
    }
  ],
  "overall_risk_level": "high",
  "recommendations": ["移除时间压力话术", "改用咨询式销售方法", "提供客观的产品信息"]
}"""
            else:
                return """{
  "is_compliant": true,
  "violations": [
    {
      "rule": "no_false_promises",
      "violated": false,
      "evidence": "",
      "severity": "low"
    },
    {
      "rule": "no_pressure",
      "violated": false,
      "evidence": "",
      "severity": "low"
    },
    {
      "rule": "transparency",
      "violated": false,
      "evidence": "",
      "severity": "low"
    }
  ],
  "overall_risk_level": "low",
  "recommendations": ["继续保持合规的销售方式"]
}"""

        return "{}"


# ==================== Test Functions ====================

async def test_graph_rag_enhanced():
    """Test Enhanced GraphRAG."""
    logger.info("=" * 60)
    logger.info("Testing Enhanced GraphRAG")
    logger.info("=" * 60)

    from app.infra.search.graph_rag_enhanced import EnhancedGraphRAGService

    # Initialize
    llm_client = MockLLMClient()
    graph_rag = EnhancedGraphRAGService(
        org_id="test_org",
        llm_client=llm_client,
        enable_multi_hop=True,
        max_reasoning_hops=3,
    )

    # Test 1: Ingest sales conversation
    logger.info("\n[Test 1] Ingesting sales conversation...")
    conversation = """
客户：你们的信用卡年费太贵了，1000元一年。
销售：我理解您的顾虑。其实我们的白金卡虽然年费1000元，
     但只要您年消费满10万，年费就全免。而且您可以享受
     机场贵宾厅、积分返现等价值超过5000元的权益。
客户：哦，这样啊。那具体有哪些权益呢？
销售：主要包括：全球机场贵宾厅、消费积分返现、生日礼遇、
     专属客服等。这些权益的市场价值远超年费。
    """

    result = await graph_rag.ingest_sales_conversation(
        conversation_id="conv_001",
        conversation_text=conversation,
        metadata={"sales_champion": "张三", "success": True}
    )

    logger.info(f"Ingestion result: {result}")
    logger.info(f"  - Entities: {result['total_entities']}")
    logger.info(f"  - Relations: {result['total_relations']}")
    logger.info(f"  - Entity types: {result['entity_types']}")

    # Test 2: Answer complex query
    logger.info("\n[Test 2] Answering complex query...")
    query = "客户说年费太贵，通常怎么应对？"

    answer_result = await graph_rag.answer_complex_query(
        query=query,
        use_multi_hop=True
    )

    logger.info(f"Query: {query}")
    logger.info(f"Answer: {answer_result['answer']}")
    logger.info(f"Confidence: {answer_result['confidence']:.2f}")
    logger.info(f"Reasoning paths: {len(answer_result['reasoning_paths'])}")

    for i, path in enumerate(answer_result['reasoning_paths'][:2], 1):
        logger.info(f"\n  Path {i}:")
        logger.info(f"    Entities: {' → '.join(path['entities'])}")
        logger.info(f"    Reasoning: {path['reasoning']}")
        logger.info(f"    Score: {path['score']:.2f}")

    # Test 3: Get stats
    logger.info("\n[Test 3] Getting statistics...")
    stats = graph_rag.get_stats()
    logger.info(f"GraphRAG stats: {stats}")

    logger.info("\n✅ Enhanced GraphRAG tests completed!")


async def test_rlaif_evaluator():
    """Test RLAIF Evaluator."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing RLAIF Evaluator")
    logger.info("=" * 60)

    from app.evaluation.rlaif_evaluator import RLAIFEvaluator

    # Initialize
    llm_client = MockLLMClient()
    evaluator = RLAIFEvaluator(llm_client)

    # Test 1: Comprehensive evaluation
    logger.info("\n[Test 1] Comprehensive evaluation...")
    customer_input = "你们的信用卡年费太贵了"
    sales_response = """我理解您的顾虑。其实我们的白金卡虽然年费1000元，
但只要您年消费满10万，年费就全免。而且您可以享受机场贵宾厅、
积分返现等价值超过5000元的权益。"""
    thought_process = """
1. 识别异议类型：价格异议
2. 建立同理心：认可客户顾虑
3. 价值转化：说明权益价值
4. 提供解决方案：消费达标免年费
    """

    evaluation = await evaluator.evaluate_comprehensive(
        customer_input=customer_input,
        sales_response=sales_response,
        thought_process=thought_process
    )

    logger.info(f"Overall score: {evaluation.overall_score:.2f}")
    logger.info("\nDimension scores:")
    for score in evaluation.dimension_scores:
        logger.info(f"  {score.dimension.value}: {score.score:.2f}")
        logger.info(f"    Reasoning: {score.reasoning}")

    logger.info(f"\nStrengths: {evaluation.strengths}")
    logger.info(f"Weaknesses: {evaluation.weaknesses}")
    logger.info(f"Suggestions: {evaluation.suggestions}")
    logger.info(f"Compliance issues: {evaluation.compliance_issues}")
    logger.info(f"Process feedback steps: {len(evaluation.process_feedback)}")

    # Test 2: Pairwise comparison
    logger.info("\n[Test 2] Pairwise comparison...")
    response_a = "年费可以免除的，您消费满10万就行。"
    response_b = """我理解您的顾虑。年费确实是一笔支出，但我们的权益价值远超年费。
只要您年消费满10万，年费就全免，而且您可以享受价值超过5000元的权益。"""

    comparison = await evaluator.pairwise_comparator.compare(
        customer_input=customer_input,
        response_a=response_a,
        response_b=response_b
    )

    logger.info(f"Preferred: {comparison.preferred}")
    logger.info(f"Confidence: {comparison.confidence:.2f}")
    logger.info(f"Reasoning: {comparison.reasoning}")

    # Test 3: Rank responses
    logger.info("\n[Test 3] Ranking responses...")
    responses = [
        ("novice", "年费可以免除..."),
        ("champion", "我理解您的顾虑..."),
        ("average", "这个价格很合理..."),
    ]

    ranked = await evaluator.rank_responses(
        customer_input=customer_input,
        responses=responses
    )

    logger.info("Ranking results:")
    for i, (response_id, score) in enumerate(ranked, 1):
        logger.info(f"  {i}. {response_id}: {score:.2f}")

    # Test 4: Constitutional checking
    logger.info("\n[Test 4] Constitutional checking...")

    # Test compliant response
    compliant_response = "我理解您的顾虑。让我为您详细介绍一下我们的权益..."
    compliant_result = await evaluator.constitutional_checker.check(compliant_response)
    logger.info("Compliant response check:")
    logger.info(f"  Is compliant: {compliant_result['is_compliant']}")
    logger.info(f"  Risk level: {compliant_result['overall_risk_level']}")

    # Test non-compliant response
    non_compliant_response = "您必须今天办理，否则明天就涨价了！"
    non_compliant_result = await evaluator.constitutional_checker.check(non_compliant_response)
    logger.info("\nNon-compliant response check:")
    logger.info(f"  Is compliant: {non_compliant_result['is_compliant']}")
    logger.info(f"  Risk level: {non_compliant_result['overall_risk_level']}")
    logger.info("  Violations:")
    for violation in non_compliant_result['violations']:
        if violation['violated']:
            logger.info(f"    - {violation['rule']}: {violation['evidence']}")
            logger.info(f"      Severity: {violation['severity']}")

    logger.info("\n✅ RLAIF Evaluator tests completed!")


async def main():
    """Run all tests."""
    logger.info("Starting GraphRAG + RLAIF tests...\n")

    try:
        # Test GraphRAG
        await test_graph_rag_enhanced()

        # Test RLAIF
        await test_rlaif_evaluator()

        logger.info("\n" + "=" * 60)
        logger.info("🎉 All tests completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
