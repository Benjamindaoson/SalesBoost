"""
Intent Classifier - MVP 意图分类服务
基于规则/轻模型的稳定分类，避免发散
"""
import logging
import re
from typing import Dict, Optional
from app.schemas.mvp import IntentLabel

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    意图分类器
    
    核心职责：
    - 稳定分类，避免发散
    - 优先使用规则，必要时使用轻模型
    - 输出 MVP 要求的 5 种意图标签
    """
    
    def __init__(self):
        # 规则库：关键词 -> 意图标签
        self.rules = {
            IntentLabel.BENEFIT_QA: [
                r"(年费|权益|优惠|活动|积分|里程|返现|免息|分期)",
                r"(有什么|哪些|怎么|如何)(权益|优惠|活动)",
                r"(能|可以)(享受|获得|使用)(什么|哪些)",
            ],
            IntentLabel.OBJECTION_HANDLING: [
                r"(太贵|价格|费用|年费|不值|考虑|犹豫|担心)",
                r"(不需要|不感兴趣|暂时|以后|再说)",
                r"(其他|别的|竞品|对比)",
                r"(风险|安全|靠谱|可信)",
            ],
            IntentLabel.CLOSING_PUSH: [
                r"(办|申请|开通|激活|下单|购买)",
                r"(现在|立即|马上|今天)(就|可以)",
                r"(确定|决定|同意|接受)",
            ],
            IntentLabel.COMPLIANCE_RISK: [
                r"(绝对|100%|肯定|一定|保证)",
                r"(最好|最强|第一|唯一)",
                r"(稳赚|保本|零风险)",
            ],
        }
        
        # 编译正则表达式
        self.compiled_rules = {
            intent: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for intent, patterns in self.rules.items()
        }
    
    def classify(self, user_message: str, context: Optional[Dict] = None) -> IntentLabel:
        """
        分类用户消息
        
        Args:
            user_message: 用户消息
            context: 可选上下文（如当前阶段、历史消息等）
            
        Returns:
            意图标签
        """
        user_lower = user_message.lower()
        
        # 优先级1：合规风险（最高优先级）
        for pattern in self.compiled_rules.get(IntentLabel.COMPLIANCE_RISK, []):
            if pattern.search(user_lower):
                logger.info(f"Classified as COMPLIANCE_RISK: {user_message[:50]}")
                return IntentLabel.COMPLIANCE_RISK
        
        # 优先级2：权益问答
        for pattern in self.compiled_rules.get(IntentLabel.BENEFIT_QA, []):
            if pattern.search(user_lower):
                logger.info(f"Classified as BENEFIT_QA: {user_message[:50]}")
                return IntentLabel.BENEFIT_QA
        
        # 优先级3：异议处理
        for pattern in self.compiled_rules.get(IntentLabel.OBJECTION_HANDLING, []):
            if pattern.search(user_lower):
                logger.info(f"Classified as OBJECTION_HANDLING: {user_message[:50]}")
                return IntentLabel.OBJECTION_HANDLING
        
        # 优先级4：推进成交
        for pattern in self.compiled_rules.get(IntentLabel.CLOSING_PUSH, []):
            if pattern.search(user_lower):
                logger.info(f"Classified as CLOSING_PUSH: {user_message[:50]}")
                return IntentLabel.CLOSING_PUSH
        
        # 默认：其他
        logger.info(f"Classified as OTHER: {user_message[:50]}")
        return IntentLabel.OTHER

