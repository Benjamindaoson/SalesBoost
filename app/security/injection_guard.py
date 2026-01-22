"""
Prompt Injection Guard
防御策略：
1. 规则匹配 (Regex) - 快速拦截已知攻击模式
2. 语义检测 (LLM/Model) - 识别复杂越狱攻击 (MVP阶段预留接口，或使用轻量级检测)
3. 编码检测 - 识别 Base64/Rot13 等混淆攻击
"""
import re
import base64
import logging
from abc import ABC, abstractmethod
from typing import Tuple, List

logger = logging.getLogger(__name__)

class BaseGuard(ABC):
    @abstractmethod
    def detect(self, text: str) -> Tuple[bool, str]:
        """
        检测文本是否包含恶意指令
        Returns:
            (is_safe, reason)
        """
        pass

class RegexGuard(BaseGuard):
    """基于正则的规则防护"""
    def __init__(self):
        self.patterns = [
            r"(ignore|disregard)\s+(all\s+)?(instructions|directions|rules)",
            r"(forget|delete)\s+(all\s+)?(instructions|rules)",
            r"system\s+prompt",
            r"you\s+are\s+(now\s+)?(a|an)\s+AI",
            r"act\s+as\s+a",
            r"role\s+play",
            r"DAN\s+mode",
            r"jailbreak",
            r"dev\s+mode",
        ]
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def detect(self, text: str) -> Tuple[bool, str]:
        for p in self._compiled:
            if p.search(text):
                return False, f"Rule match: {p.pattern}"
        return True, "OK"

class EncodingGuard(BaseGuard):
    """检测异常编码或混淆"""
    def detect(self, text: str) -> Tuple[bool, str]:
        # 1. 长度检测 (避免过长输入导致 DoS)
        if len(text) > 4000:
            return False, "Input too long"
            
        # 2. Base64 探测 (简单的启发式: 连续大量无空格字符且符合b64特征)
        # 仅当疑似 base64 且解码后包含恶意关键词时拦截
        words = text.split()
        for word in words:
            if len(word) > 20 and re.match(r'^[A-Za-z0-9+/]+={0,2}$', word):
                try:
                    decoded = base64.b64decode(word).decode('utf-8', errors='ignore')
                    # 递归检查解码内容
                    if "system prompt" in decoded.lower() or "ignore instructions" in decoded.lower():
                        return False, "Malicious Base64 content detected"
                except:
                    pass
        
        return True, "OK"

class CompositeGuard(BaseGuard):
    """组合防护器"""
    def __init__(self):
        self.guards: List[BaseGuard] = [
            EncodingGuard(),
            RegexGuard(),
            # Future: LLMGuard()
        ]
    
    def detect(self, text: str) -> Tuple[bool, str]:
        for guard in self.guards:
            is_safe, reason = guard.detect(text)
            if not is_safe:
                logger.warning(f"Security Alert: {reason}")
                return False, reason
        return True, "OK"

# 全局单例
prompt_guard = CompositeGuard()
