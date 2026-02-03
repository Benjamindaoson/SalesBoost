"""
Intent Recognition & Dynamic RAG Routing

Phase 3B Week 5 Day 5-6 交付物

集成到 SalesBoost agent 架构的意图识别和路由模块
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class UserIntent(str, Enum):
    """用户意图类型"""
    INFORMATIONAL = "informational"
    SOCIAL = "social"
    OBJECTION = "objection"
    BUYING_SIGNAL = "buying_signal"
    CLARIFICATION = "clarification"
    UNKNOWN = "unknown"


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
    """意图路由器"""

    def __init__(self):
        self._initialize_patterns()

    def _initialize_patterns(self):
        """初始化意图识别模式"""

        self.informational_keywords = [
            "年费", "额度", "权益", "积分", "优惠", "费用", "利率", "还款",
            "申请", "办理", "条件", "要求", "资格", "审批",
            "annual fee", "credit limit", "benefit", "points", "interest rate",
            "什么", "怎么", "如何", "多少", "哪些", "有没有", "能不能",
            "what", "how", "which", "can", "do"
        ]

        self.social_keywords = [
            "你好", "您好", "早上好", "下午好", "晚上好",
            "谢谢", "感谢", "不客气",
            "再见", "拜拜",
            "天气", "吃饭", "休息",
            "hello", "hi", "thanks", "bye"
        ]

        self.objection_keywords = [
            "太贵", "贵了", "便宜", "降价", "优惠",
            "expensive", "cheap", "discount",
            "不需要", "不想要", "不感兴趣", "有卡了",
            "don't need", "not interested",
            "考虑", "再说", "以后", "不急",
            "think about", "later",
            "不相信", "有坑", "骗人", "靠谱",
            "don't trust", "scam"
        ]

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
        """分析用户消息的意图"""
        message_lower = message.lower()

        # 1. BUYING_SIGNAL
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

        # 2. OBJECTION
        objection_matches = self._match_keywords(message_lower, self.objection_keywords)
        if objection_matches:
            return IntentAnalysis(
                intent=UserIntent.OBJECTION,
                confidence=0.85,
                keywords=objection_matches,
                reasoning="检测到异议关键词",
                requires_rag=False,
                suggested_action="进入 Objection 阶段，处理客户顾虑"
            )

        # 3. INFORMATIONAL
        info_matches = self._match_keywords(message_lower, self.informational_keywords)
        if info_matches:
            return IntentAnalysis(
                intent=UserIntent.INFORMATIONAL,
                confidence=0.8,
                keywords=info_matches,
                reasoning="检测到信息查询关键词",
                requires_rag=True,
                suggested_action="调用 RAG 检索产品信息"
            )

        # 4. SOCIAL
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

        # 5. UNKNOWN
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
    """行动路由器"""

    def __init__(self, knowledge_interface=None):
        self.intent_router = IntentRouter()
        self.knowledge = knowledge_interface

    async def route_action(
        self,
        message: str,
        conversation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """路由行动"""
        intent_analysis = self.intent_router.analyze_intent(message, conversation_context)

        logger.info(
            f"Intent analysis: {intent_analysis.intent.value} "
            f"(confidence: {intent_analysis.confidence:.2f})"
        )

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

        if intent_analysis.requires_rag and self.knowledge:
            try:
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

        elif intent_analysis.intent == UserIntent.BUYING_SIGNAL:
            action["recommended_response"] = "太好了！那我现在帮您办理，需要您提供一下身份证信息..."

        elif intent_analysis.intent == UserIntent.OBJECTION:
            action["recommended_response"] = "我理解您的顾虑。能具体说说您担心的是什么吗？"

        elif intent_analysis.intent == UserIntent.SOCIAL:
            action["recommended_response"] = ""

        return action

    def _format_rag_response(self, rag_results: Dict[str, Any]) -> str:
        """格式化 RAG 检索结果"""
        if not rag_results.get("found"):
            return ""

        data = rag_results.get("data", [])
        if not data:
            return ""

        top_results = data[:3]

        formatted = "根据我们的产品信息：\n\n"
        for i, result in enumerate(top_results, 1):
            text = result.get("text", "")
            formatted += f"{i}. {text}\n\n"

        return formatted.strip()
