import re
import time
from enum import Enum
from typing import List, Dict, Tuple
from dataclasses import dataclass
from collections import Counter

class IntentCategory(str, Enum):
    CREATIVE = "creative"       # Storytelling, marketing copy
    LOGIC = "logic"             # Math, coding, reasoning
    EXTRACTION = "extraction"   # Summarization, data extraction
    SIMPLE_CHAT = "simple_chat" # Greetings, simple Q&A

@dataclass
class FastIntentResult:
    category: IntentCategory
    confidence: float
    latency_ms: float

class FastIntentClassifier:
    """
    Ultra-low latency intent classifier for LLM routing.
    Target latency: < 20ms.
    Strategy: Regex/Keyword -> Heuristics -> (Future: FastText)
    """

    def __init__(self):
        # 1. Regex Patterns for Logic/Code
        self.logic_patterns = [
            re.compile(r"\b(code|python|function|api|bug|error|calculate|solve|math|equation|compute)\b", re.IGNORECASE),
            re.compile(r"```"),  # Code blocks
            re.compile(r"[+\-*/=]{2,}"),  # Math symbols
        ]

        self.logic_keywords_zh = (
            "代码", "写代码", "函数", "报错", "错误", "异常", "修复", "调试", "debug",
            "算法", "复杂度", "时间复杂度", "空间复杂度", "计算", "推导", "证明", "方程", "积分", "微分",
            "概率", "统计", "公式", "实现", "接口", "api", "bug",
        )
        
        # 2. Regex Patterns for Creative/Writing
        self.creative_patterns = [
            re.compile(r"\b(write|compose|story|poem|email|blog|post|article|creative|imagine|draft)\b", re.IGNORECASE),
        ]

        self.creative_keywords_zh = (
            "写一篇", "写个", "写封", "文案", "广告", "宣传", "标题", "起名", "slogan", "脚本",
            "润色", "改写", "扩写", "缩写", "写作", "故事", "小说", "诗", "公众号", "朋友圈",
        )
        
        # 3. Regex Patterns for Extraction/Analysis
        self.extraction_patterns = [
            re.compile(r"\b(summarize|extract|analyze|list|table|key points|summary|json|format)\b", re.IGNORECASE),
        ]

        self.extraction_keywords_zh = (
            "总结", "概括", "提取", "抽取", "整理", "列出", "列表", "表格", "要点",
            "结构化", "转成", "输出json", "json格式", "格式化", "解析", "字段", "key points",
        )
        
        # Stats Tracking
        self.stats = Counter()

    def get_stats(self) -> Dict[str, int]:
        return dict(self.stats)

    def classify(self, prompt: str) -> FastIntentResult:
        start_time = time.perf_counter()
        result = self._classify_logic(prompt, start_time)
        
        # Update stats
        self.stats[result.category] += 1
        
        return result

    def _classify_logic(self, prompt: str, start_time: float) -> FastIntentResult:
        prompt = prompt or ""
        prompt_lower = prompt.lower()

        # 1. Length Heuristic (Extraction/Context Heavy)
        # If prompt is very long, it's likely analysis or extraction
        if len(prompt) > 8000: # ~2000 tokens approx
            latency = (time.perf_counter() - start_time) * 1000
            return FastIntentResult(IntentCategory.EXTRACTION, 0.95, latency)

        # 2. Keyword/Regex Matching (Priority: Logic > Extraction > Creative)
        # Logic/Math/Code usually requires smarter models
        for pattern in self.logic_patterns:
            if pattern.search(prompt):
                latency = (time.perf_counter() - start_time) * 1000
                return FastIntentResult(IntentCategory.LOGIC, 0.9, latency)

        if any(k in prompt for k in self.logic_keywords_zh):
            latency = (time.perf_counter() - start_time) * 1000
            return FastIntentResult(IntentCategory.LOGIC, 0.88, latency)
        
        # Extraction
        for pattern in self.extraction_patterns:
            if pattern.search(prompt):
                latency = (time.perf_counter() - start_time) * 1000
                return FastIntentResult(IntentCategory.EXTRACTION, 0.85, latency)

        if any(k in prompt for k in self.extraction_keywords_zh):
            latency = (time.perf_counter() - start_time) * 1000
            return FastIntentResult(IntentCategory.EXTRACTION, 0.82, latency)

        # Creative
        for pattern in self.creative_patterns:
            if pattern.search(prompt):
                latency = (time.perf_counter() - start_time) * 1000
                return FastIntentResult(IntentCategory.CREATIVE, 0.85, latency)

        if any(k in prompt for k in self.creative_keywords_zh):
            latency = (time.perf_counter() - start_time) * 1000
            return FastIntentResult(IntentCategory.CREATIVE, 0.82, latency)

        # 3. Default Fallback
        latency = (time.perf_counter() - start_time) * 1000
        return FastIntentResult(IntentCategory.SIMPLE_CHAT, 0.7, latency)

# Global Instance
fast_intent_classifier = FastIntentClassifier()
