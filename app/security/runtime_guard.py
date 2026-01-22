import logging
import re
from typing import Tuple, List, Optional
from app.schemas.trace import SecurityEvent

logger = logging.getLogger(__name__)

class SecurityAction:
    PASS = "allow"
    BLOCK = "block"
    REWRITE = "rewrite"
    DOWNGRADE = "downgrade" # 新增降级
    WARN = "warn"

class RuntimeGuard:
    """
    V3 运行时安全护栏
    负责输入防护、输出拦截与风险降级
    """
    def __init__(self):
        self.injection_patterns = [
            (re.compile(r"(ignore|disregard|forget)\s+(all\s+)?(instructions|rules|directions)", re.I), "instruction_bypass"),
            (re.compile(r"system\s+prompt", re.I), "system_prompt_leak"),
            (re.compile(r"you\s+are\s+now\s+a", re.I), "role_jailbreak"),
        ]
        self.forbidden_expressions = [
            (re.compile(r"价格太贵了", re.I), "negative_pricing_loop"),
            (re.compile(r"我不知道", re.I), "low_confidence_refusal"),
        ]
        self.high_risk_keywords = [
            (re.compile(r"退款", re.I), "refund_risk"),
            (re.compile(r"投诉", re.I), "complaint_risk"),
        ]

    def check_input(self, text: str) -> Tuple[str, Optional[SecurityEvent]]:
        """输入层检测"""
        # 1. Injection Check (Block)
        for pattern, rule_id in self.injection_patterns:
            if pattern.search(text):
                event = SecurityEvent(
                    event_type="input_injection",
                    action_taken=SecurityAction.BLOCK,
                    rule_id=rule_id,
                    trigger_point="pre_generate",
                    reason=f"Matched pattern: {pattern.pattern}"
                )
                return SecurityAction.BLOCK, event
        
        # 2. High Risk Check (Downgrade)
        for pattern, rule_id in self.high_risk_keywords:
             if pattern.search(text):
                event = SecurityEvent(
                    event_type="high_risk_input",
                    action_taken=SecurityAction.DOWNGRADE,
                    rule_id=rule_id,
                    trigger_point="pre_generate",
                    reason=f"High risk keyword detected: {pattern.pattern}"
                )
                return SecurityAction.DOWNGRADE, event

        return SecurityAction.PASS, None

    def check_output(self, text: str) -> Tuple[str, str, Optional[SecurityEvent]]:
        """输出层检测与改写"""
        modified_text = text
        triggered_event = None

        for pattern, rule_id in self.forbidden_expressions:
            if pattern.search(text):
                # 简单改写示例
                modified_text = pattern.sub("关于价格，我们可以探讨其带来的价值", modified_text)
                triggered_event = SecurityEvent(
                    event_type="output_forbidden",
                    action_taken=SecurityAction.REWRITE,
                    rule_id=rule_id,
                    trigger_point="post_generate",
                    reason=f"Intercepted forbidden expression: {pattern.pattern}"
                )
        
        return SecurityAction.REWRITE if triggered_event else SecurityAction.PASS, modified_text, triggered_event

    def assess_risk_level(self, context: str) -> int:
        """评估当前上下文风险等级 (0-10)"""
        risk = 0
        if "价格" in context or "折扣" in context:
            risk += 3
        if "投诉" in context or "生气" in context:
            risk += 5
        return risk

# 单例
runtime_guard = RuntimeGuard()
