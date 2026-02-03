"""
Phase 3B Week 5 Day 5-6: Intent Recognition & Dynamic RAG Routing

核心目标：解决"什么时候该查库，什么时候该闲聊"的问题。

意图类型：
1. INFORMATIONAL: 需要查询产品信息 -> 调用 RAG
2. SOCIAL: 闲聊、寒暄 -> 纯 LLM
3. OBJECTION: 异议处理 -> 调用异议处理库
4. BUYING_SIGNAL: 购买信号 -> 触发缔结脚本

实现日期: 2026-02-02
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


class UserIntent(str, Enum):
    """用户意图类型"""
    INFORMATIONAL = "informational"      # 信息查询
    SOCIAL = "social"                    # 社交闲聊
    OBJECTION = "objection"              # 异议表达
    BUYING_SIGNAL = "buying_signal"      # 购买信号
    CLARIFICATION = "clarification"      # 澄清确认
    UNKNOWN = "unknown"                  # 未知意图


@dataclass
class IntentAnalysis:
    """意图分析结果"""
    intent: UserIntent
    confidence: float
    keywords: List[str]
    reasoning: str
    requires_rag: bool
    suggested_action: str


class IntentRouter:
    """
    意图路由器

    核心功能：
    1. 分析用户消息的意图
    2. 决定是否需要调用 RAG
    3. 提供行动建议
    """

    def __init__(self):
        self._initialize_patterns()

    def _initialize_patterns(self):
        """初始化意图识别模式"""

        # INFORMATIONAL 意图关键词
        self.informational_keywords = [
            # 产品信息
            "年费", "额度", "权益", "积分", "优惠", "费用", "利率", "还款",
            "申请", "办理", "条件", "要求", "资格", "审批",
            # 英文
            "annual fee", "credit limit", "benefit", "points", "interest rate",
            # 疑问词
            "什么", "怎么", "如何", "多少", "哪些", "有没有", "能不能",
            "what", "how", "which", "can", "do"
        ]

        # SOCIAL 意图关键词
        self.social_keywords = [
            "你好", "您好", "早上好", "下午好", "晚上好",
            "谢谢", "感谢", "不客气",
            "再见", "拜拜",
            "天气", "吃饭", "休息",
            "hello", "hi", "thanks", "bye"
        ]

        # OBJECTION 意图关键词
        self.objection_keywords = [
            # 价格异议
            "太贵", "贵了", "便宜", "降价", "优惠",
            "expensive", "cheap", "discount",
            # 需求异议
            "不需要", "不想要", "不感兴趣", "有卡了",
            "don't need", "not interested",
            # 时机异议
            "考虑", "再说", "以后", "不急",
            "think about", "later",
            # 信任异议
            "不相信", "有坑", "骗人", "靠谱",
            "don't trust", "scam"
        ]

        # BUYING_SIGNAL 意图关键词
        self.buying_signal_keywords = [
            "办理", "申请", "开卡", "激活",
            "好的", "可以", "行", "就这个", "要了",
            "怎么办", "流程", "需要什么",
            "apply", "ok", "yes", "sure", "deal"
        ]

        logger.info("Initialized intent recognition patterns")

    def analyze_intent(
        self,
        message: str,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> IntentAnalysis:
        """
        分析用户消息的意图

        Args:
            message: 用户消息
            conversation_context: 对话上下文（可选）

        Returns:
            IntentAnalysis: 意图分析结果
        """
        message_lower = message.lower()

        # 1. 检查 BUYING_SIGNAL
        buying_matches = self._match_keywords(message_lower, self.buying_signal_keywords)
        if buying_matches:
            return IntentAnalysis(
                intent=UserIntent.BUYING_SIGNAL,
                confidence=0.9,
                keywords=buying_matches,
                reasoning="检测到购买信号关键词",
                requires_rag=False,
                suggested_action="进入 Closing 阶段，推进成交"
            )

        # 2. 检查 OBJECTION
        objection_matches = self._match_keywords(message_lower, self.objection_keywords)
        if objection_matches:
            return IntentAnalysis(
                intent=UserIntent.OBJECTION,
                confidence=0.85,
                keywords=objection_matches,
                reasoning="检测到异议关键词",
                requires_rag=False,  # 异议处理通常不需要 RAG
                suggested_action="进入 Objection 阶段，处理客户顾虑"
            )

        # 3. 检查 INFORMATIONAL
        info_matches = self._match_keywords(message_lower, self.informational_keywords)
        if info_matches:
            return IntentAnalysis(
                intent=UserIntent.INFORMATIONAL,
                confidence=0.8,
                keywords=info_matches,
                reasoning="检测到信息查询关键词",
                requires_rag=True,  # 需要调用 RAG
                suggested_action="调用 RAG 检索产品信息"
            )

        # 4. 检查 SOCIAL
        social_matches = self._match_keywords(message_lower, self.social_keywords)
        if social_matches:
            return IntentAnalysis(
                intent=UserIntent.SOCIAL,
                confidence=0.75,
                keywords=social_matches,
                reasoning="检测到社交闲聊关键词",
                requires_rag=False,
                suggested_action="使用纯 LLM 进行自然对话"
            )

        # 5. 默认为 UNKNOWN
        return IntentAnalysis(
            intent=UserIntent.UNKNOWN,
            confidence=0.5,
            keywords=[],
            reasoning="未匹配到明确意图",
            requires_rag=False,
            suggested_action="根据当前销售阶段继续对话"
        )

    def _match_keywords(self, message: str, keywords: List[str]) -> List[str]:
        """匹配关键词"""
        matches = []
        for keyword in keywords:
            if keyword in message:
                matches.append(keyword)
        return matches


class ActionRouter:
    """
    行动路由器

    核心功能：
    1. 根据意图决定具体行动
    2. 集成 RAG 调用
    3. 集成 FSM 状态转换
    """

    def __init__(self, knowledge_interface=None):
        self.intent_router = IntentRouter()
        self.knowledge = knowledge_interface  # Phase 3A 的 RAG 系统

    async def route_action(
        self,
        message: str,
        conversation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        路由行动

        Args:
            message: 用户消息
            conversation_context: 对话上下文

        Returns:
            行动决策
        """
        # 1. 分析意图
        intent_analysis = self.intent_router.analyze_intent(message, conversation_context)

        logger.info(
            f"Intent analysis: {intent_analysis.intent.value} "
            f"(confidence: {intent_analysis.confidence:.2f})"
        )

        # 2. 根据意图路由行动
        action = {
            "intent": intent_analysis.intent.value,
            "confidence": intent_analysis.confidence,
            "keywords": intent_analysis.keywords,
            "reasoning": intent_analysis.reasoning,
            "requires_rag": intent_analysis.requires_rag,
            "suggested_action": intent_analysis.suggested_action,
            "rag_results": None,
            "recommended_response": ""
        }

        # 3. 如果需要 RAG，调用知识库
        if intent_analysis.requires_rag and self.knowledge:
            try:
                # 调用 Phase 3A 的知识接口
                rag_results = self.knowledge.get_product_info(
                    query=message,
                    exact_match=False
                )

                if rag_results.get("found"):
                    action["rag_results"] = rag_results
                    action["recommended_response"] = self._format_rag_response(rag_results)
                    logger.info(f"RAG retrieved {len(rag_results.get('data', []))} results")
                else:
                    logger.warning("RAG query returned no results")
                    action["recommended_response"] = "抱歉，我暂时没有找到相关信息。您能具体说说您想了解什么吗？"

            except Exception as e:
                logger.error(f"RAG query failed: {e}")
                action["recommended_response"] = "系统查询出现问题，请稍后再试。"

        # 4. 根据意图类型提供建议
        elif intent_analysis.intent == UserIntent.BUYING_SIGNAL:
            action["recommended_response"] = "太好了！那我现在帮您办理，需要您提供一下身份证信息..."

        elif intent_analysis.intent == UserIntent.OBJECTION:
            action["recommended_response"] = "我理解您的顾虑。能具体说说您担心的是什么吗？"

        elif intent_analysis.intent == UserIntent.SOCIAL:
            action["recommended_response"] = ""  # 由 LLM 自然生成

        return action

    def _format_rag_response(self, rag_results: Dict[str, Any]) -> str:
        """格式化 RAG 检索结果"""
        if not rag_results.get("found"):
            return ""

        data = rag_results.get("data", [])
        if not data:
            return ""

        # 取前3个结果
        top_results = data[:3]

        formatted = "根据我们的产品信息：\n\n"
        for i, result in enumerate(top_results, 1):
            text = result.get("text", "")
            formatted += f"{i}. {text}\n\n"

        return formatted.strip()


# ============================================================================
# 测试和演示
# ============================================================================

def demo_intent_routing():
    """演示意图识别和路由"""
    print("=" * 80)
    print("Phase 3B Week 5 Day 5-6: Intent Recognition & Routing Demo")
    print("=" * 80)

    router = IntentRouter()

    # 测试用例
    test_cases = [
        ("你好，我想了解一下信用卡", "开场"),
        ("年费多少钱？", "信息查询"),
        ("太贵了，能便宜点吗？", "价格异议"),
        ("我不需要信用卡", "需求异议"),
        ("好的，我要办理", "购买信号"),
        ("今天天气不错", "闲聊"),
        ("这张卡有什么权益？", "信息查询"),
        ("我再考虑考虑", "时机异议"),
        ("怎么申请？", "购买信号"),
        ("谢谢你的介绍", "社交")
    ]

    print("\n[Intent Analysis Results]")
    print("-" * 80)

    for message, expected in test_cases:
        analysis = router.analyze_intent(message)

        print(f"\nMessage: \"{message}\"")
        print(f"Expected: {expected}")
        print(f"Detected Intent: {analysis.intent.value}")
        print(f"Confidence: {analysis.confidence:.2f}")
        print(f"Keywords: {', '.join(analysis.keywords) if analysis.keywords else 'None'}")
        print(f"Requires RAG: {analysis.requires_rag}")
        print(f"Suggested Action: {analysis.suggested_action}")

    # 统计准确率
    print("\n" + "=" * 80)
    print("Intent Distribution")
    print("=" * 80)

    intent_counts = {}
    for message, _ in test_cases:
        analysis = router.analyze_intent(message)
        intent = analysis.intent.value
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    for intent, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{intent}: {count} ({count/len(test_cases)*100:.1f}%)")

    print("\n[OK] Demo completed successfully!")


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行演示
    demo_intent_routing()
