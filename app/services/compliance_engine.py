"""
Rule-Based Compliance Engine - 基于规则的合规引擎 (简化版)
将合规检查从LLM迁移到确定性规则引擎，提高可靠性和降低成本
"""

import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import time

from app.services.logging_service import structured_logger


class ComplianceLevel(Enum):
    """合规等级"""

    PASS = "pass"  # 完全合规
    WARNING = "warning"  # 轻微违规，警告
    ERROR = "error"  # 严重违规，错误
    BLOCK = "block"  # 严重违规，阻止


class ViolationType(Enum):
    """违规类型"""

    SENSITIVE_INFO = "sensitive_info"  # 敏感信息
    INAPPROPRIATE_LANGUAGE = "inappropriate_language"  # 不当语言
    PRIVACY_VIOLATION = "privacy_violation"  # 隐私违规
    BUSINESS_ETHICS = "business_ethics"  # 商业伦理
    REGULATORY_COMPLIANCE = "regulatory_compliance"  # 法规合规


@dataclass
class ComplianceRule:
    """合规规则"""

    name: str
    description: str
    violation_type: ViolationType
    level: ComplianceLevel
    pattern: Optional[str] = None
    keywords: List[str] = None
    enabled: bool = True

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


@dataclass
class ComplianceResult:
    """合规检查结果"""

    is_compliant: bool
    violations: List[Dict[str, Any]]
    score: float  # 0-100
    processing_time_ms: float
    rules_checked: int
    triggered_rules: List[str]


class ComplianceRuleEngine:
    """合规规则引擎"""

    def __init__(self):
        self.rules = self._load_default_rules()

    def _load_default_rules(self) -> Dict[str, ComplianceRule]:
        """加载默认合规规则"""
        return {
            # 敏感信息检测
            "phone_number": ComplianceRule(
                name="phone_number",
                description="检测电话号码",
                violation_type=ViolationType.SENSITIVE_INFO,
                level=ComplianceLevel.WARNING,
                pattern=r"(\+86)?1[3-9]\d{9}|0\d{2,3}-?\d{7,8}",
            ),
            "email_address": ComplianceRule(
                name="email_address",
                description="检测邮箱地址",
                violation_type=ViolationType.SENSITIVE_INFO,
                level=ComplianceLevel.WARNING,
                pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            ),
            "id_card": ComplianceRule(
                name="id_card",
                description="检测身份证号",
                violation_type=ViolationType.SENSITIVE_INFO,
                level=ComplianceLevel.ERROR,
                pattern=r"\b\d{15}|\d{17}[0-9Xx]\b",
            ),
            "bank_card": ComplianceRule(
                name="bank_card",
                description="检测银行卡号",
                violation_type=ViolationType.SENSITIVE_INFO,
                level=ComplianceLevel.ERROR,
                pattern=r"\b\d{16,19}\b",
            ),
            # 不当语言检测
            "profanity": ComplianceRule(
                name="profanity",
                description="检测不当语言",
                violation_type=ViolationType.INAPPROPRIATE_LANGUAGE,
                level=ComplianceLevel.WARNING,
                keywords=["他妈的", "操", "傻逼", "垃圾", "滚", "去死"],
            ),
            "discrimination": ComplianceRule(
                name="discrimination",
                description="检测歧视性语言",
                violation_type=ViolationType.INAPPROPRIATE_LANGUAGE,
                level=ComplianceLevel.ERROR,
                keywords=["性别歧视", "种族歧视", "年龄歧视", "地域黑"],
            ),
            # 商业伦理
            "false_promise": ComplianceRule(
                name="false_promise",
                description="检测虚假承诺",
                violation_type=ViolationType.BUSINESS_ETHICS,
                level=ComplianceLevel.WARNING,
                keywords=["保证", "一定", "绝对", "100%", "包过", "必成"],
            ),
            "price_violation": ComplianceRule(
                name="price_violation",
                description="检测价格违规",
                violation_type=ViolationType.BUSINESS_ETHICS,
                level=ComplianceLevel.ERROR,
                keywords=["回扣", "返点", "佣金", "好处费"],
            ),
            # 法规合规
            "medical_advice": ComplianceRule(
                name="medical_advice",
                description="检测医疗建议",
                violation_type=ViolationType.REGULATORY_COMPLIANCE,
                level=ComplianceLevel.BLOCK,
                keywords=["治疗", "药方", "诊断", "处方", "疗效"],
            ),
            "financial_advice": ComplianceRule(
                name="financial_advice",
                description="检测投资建议",
                violation_type=ViolationType.REGULATORY_COMPLIANCE,
                level=ComplianceLevel.WARNING,
                keywords=["投资", "股票", "基金", "收益", "分红"],
            ),
        }

    def check_compliance(self, text: str, context: Optional[Dict] = None) -> ComplianceResult:
        """执行合规检查"""
        start_time = time.time()
        violations = []
        triggered_rules = []
        rules_checked = 0

        # 基础规则检查
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue

            rules_checked += 1
            violation = self._check_single_rule(text, rule, context)

            if violation:
                violations.append(violation)
                triggered_rules.append(rule_name)

        # 计算合规分数
        score = self._calculate_compliance_score(violations)
        is_compliant = len([v for v in violations if v["level"] in ["error", "block"]]) == 0

        processing_time_ms = (time.time() - start_time) * 1000

        return ComplianceResult(
            is_compliant=is_compliant,
            violations=violations,
            score=score,
            processing_time_ms=processing_time_ms,
            rules_checked=rules_checked,
            triggered_rules=triggered_rules,
        )

    def _check_single_rule(self, text: str, rule: ComplianceRule, context: Optional[Dict] = None) -> Optional[Dict]:
        """检查单个规则"""
        text_lower = text.lower()

        # 正则表达式检查
        if rule.pattern:
            matches = re.findall(rule.pattern, text, re.IGNORECASE)
            if matches:
                return {
                    "rule_name": rule.name,
                    "violation_type": rule.violation_type.value,
                    "level": rule.level.value,
                    "description": rule.description,
                    "matches": matches[:5],  # 限制返回数量
                    "match_count": len(matches),
                }

        # 关键词检查
        if rule.keywords:
            found_keywords = []
            for keyword in rule.keywords:
                if keyword.lower() in text_lower:
                    found_keywords.append(keyword)

            if found_keywords:
                return {
                    "rule_name": rule.name,
                    "violation_type": rule.violation_type.value,
                    "level": rule.level.value,
                    "description": rule.description,
                    "found_keywords": found_keywords,
                    "match_count": len(found_keywords),
                }

        return None

    def _calculate_compliance_score(self, violations: List[Dict]) -> float:
        """计算合规分数 (0-100)"""
        if not violations:
            return 100.0

        # 根据违规等级扣分
        level_penalties = {"pass": 0, "warning": 10, "error": 30, "block": 50}

        total_penalty = 0
        for violation in violations:
            total_penalty += level_penalties.get(violation.get("level", "warning"), 10)

        # 分数不低于0
        score = max(0, 100 - total_penalty)
        return round(score, 1)

    def add_custom_rule(self, rule: ComplianceRule):
        """添加自定义规则"""
        self.rules[rule.name] = rule

        structured_logger.log_business_event(
            "custom_rule_added",
            user_id="admin",
            session_id="rule_engine",
            details={"rule_name": rule.name, "violation_type": rule.violation_type.value, "level": rule.level.value},
        )

    def enable_rule(self, rule_name: str, enabled: bool = True):
        """启用/禁用规则"""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = enabled

            structured_logger.log_business_event(
                "rule_status_changed",
                user_id="admin",
                session_id="rule_engine",
                details={"rule_name": rule_name, "enabled": enabled},
            )

    def get_rule_statistics(self) -> Dict:
        """获取规则统计信息"""
        total_rules = len(self.rules)
        enabled_rules = len([r for r in self.rules.values() if r.enabled])

        rules_by_type = {}
        rules_by_level = {}

        for rule in self.rules.values():
            # 按类型统计
            vtype = rule.violation_type.value
            rules_by_type[vtype] = rules_by_type.get(vtype, 0) + 1

            # 按等级统计
            level = rule.level.value
            rules_by_level[level] = rules_by_level.get(level, 0) + 1

        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "rules_by_type": rules_by_type,
            "rules_by_level": rules_by_level,
        }


# 全局实例
compliance_engine = ComplianceRuleEngine()


# 导出主要类
__all__ = [
    "ComplianceLevel",
    "ViolationType",
    "ComplianceRule",
    "ComplianceResult",
    "ComplianceRuleEngine",
    "compliance_engine",
]
