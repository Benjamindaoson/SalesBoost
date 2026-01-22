"""
Prompt Injection Guard
用于检测和拦截恶意 Prompt
"""
import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

class PromptInjectionGuard:
    def __init__(self):
        # 常见注入模式
        self.injection_patterns = [
            r"ignore (all )?previous instructions",
            r"ignore (the )?above instructions",
            r"system prompt",
            r"you are not",
            r"reset your role",
            r"jailbreak",
            r"DAN mode",
            r"developer mode",
            r"act as an unrestricted AI",
            r"override",
        ]
        
        # 敏感词库 (简单示例)
        self.sensitive_keywords = [
            "password", "secret key", "admin token", "credential"
        ]
        
    def detect(self, text: str) -> Tuple[bool, str]:
        """
        检测输入是否包含 Prompt Injection
        Returns: (is_safe, reason)
        """
        text_lower = text.lower()
        
        # 1. 模式匹配
        for pattern in self.injection_patterns:
            if re.search(pattern, text_lower):
                logger.warning(f"Prompt injection detected: {pattern} in '{text[:50]}...'")
                return False, f"Detected injection pattern: {pattern}"
                
        # 2. 敏感词检测
        for keyword in self.sensitive_keywords:
            if keyword in text_lower:
                logger.warning(f"Sensitive keyword detected: {keyword} in '{text[:50]}...'")
                return False, f"Detected sensitive keyword: {keyword}"
                
        # 3. 长度/复杂度检测 (可选)
        if len(text) > 2000: # 限制单次输入长度
             return False, "Input too long"

        return True, "Safe"

    def sanitize(self, text: str) -> str:
        """
        清洗输入（简单实现）
        """
        # 可以移除不可见字符等
        return text.strip()

# 全局单例
prompt_guard = PromptInjectionGuard()
