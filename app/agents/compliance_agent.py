"""
Compliance Agent
100% 拦截高风险词汇（夸大、误导性承诺）
提供安全替代表述
"""
import logging
import re
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.schemas.agent_outputs import ComplianceOutput, RiskFlag
from app.schemas.fsm import SalesStage

logger = logging.getLogger(__name__)


# 高风险词汇库（必须 100% 拦截）
HIGH_RISK_PATTERNS: Dict[str, Dict[str, Any]] = {
    # 夸大类
    r"(绝对|100%|完全|肯定|一定)(能|会|可以|保证)": {
        "risk_type": "exaggeration",
        "severity": "high",
        "reason": "使用绝对化承诺，可能构成虚假宣传",
        "alternative": "根据过往经验，大多数情况下可以...",
    },
    r"(最好|最强|最优|第一|唯一|独家)": {
        "risk_type": "exaggeration",
        "severity": "high",
        "reason": "使用极限词，违反广告法",
        "alternative": "我们的产品在XX方面表现优秀...",
    },
    r"(永远|永久|终身)(免费|有效|保障)": {
        "risk_type": "exaggeration",
        "severity": "high",
        "reason": "无限期承诺，存在法律风险",
        "alternative": "在合同期内，您可以享受...",
    },
    # 误导类
    r"(不可能|绝不会)(出问题|有风险|亏损)": {
        "risk_type": "misleading",
        "severity": "high",
        "reason": "误导性承诺，隐瞒风险",
        "alternative": "我们有完善的风控机制，但任何投资都有风险...",
    },
    r"(稳赚|保本|零风险|无风险)": {
        "risk_type": "misleading",
        "severity": "high",
        "reason": "虚假承诺收益，违反金融法规",
        "alternative": "根据历史数据，收益表现稳定，但不代表未来...",
    },
    r"(内部消息|内幕|小道消息)": {
        "risk_type": "misleading",
        "severity": "high",
        "reason": "暗示内幕信息，可能违法",
        "alternative": "根据公开信息和专业分析...",
    },
    # 禁止类
    r"(竞争对手|友商)(垃圾|不行|骗子|坑人)": {
        "risk_type": "prohibited",
        "severity": "high",
        "reason": "贬低竞争对手，违反商业道德",
        "alternative": "我们专注于自身产品优势...",
    },
    r"(送礼|回扣|返点|好处费)": {
        "risk_type": "prohibited",
        "severity": "high",
        "reason": "涉嫌商业贿赂",
        "alternative": "我们提供正规的优惠政策...",
    },
    r"(私下|私人)(转账|打款|交易)": {
        "risk_type": "prohibited",
        "severity": "high",
        "reason": "涉嫌违规操作",
        "alternative": "所有交易请通过官方渠道...",
    },
}

# 中风险词汇（警告但不拦截）
MEDIUM_RISK_PATTERNS: Dict[str, Dict[str, Any]] = {
    r"(很多|大量)(客户|用户|公司)(都在用|选择了)": {
        "risk_type": "exaggeration",
        "severity": "medium",
        "reason": "模糊的数量表述，建议提供具体数据",
        "alternative": "目前已有XX家客户选择了我们...",
    },
    r"(马上|立刻|很快)(见效|回本|盈利)": {
        "risk_type": "misleading",
        "severity": "medium",
        "reason": "时间承诺过于模糊",
        "alternative": "根据实施计划，预计在XX周期内...",
    },
}


class ComplianceAgent(BaseAgent):
    """
    合规检查 Agent
    
    核心职责：
    - 100% 拦截高风险词汇
    - 检测夸大、误导性承诺
    - 提供安全替代表述
    - 支持自定义规则扩展
    
    风险等级：
    - high: 必须拦截，不允许发送
    - medium: 警告，建议修改
    - low: 提示，可选修改
    """
    
    def __init__(self, **kwargs):
        super().__init__(temperature=0.1, **kwargs)
        self.high_risk_patterns = HIGH_RISK_PATTERNS
        self.medium_risk_patterns = MEDIUM_RISK_PATTERNS
        self._compiled_high_patterns = {
            re.compile(pattern, re.IGNORECASE): info
            for pattern, info in HIGH_RISK_PATTERNS.items()
        }
        self._compiled_medium_patterns = {
            re.compile(pattern, re.IGNORECASE): info
            for pattern, info in MEDIUM_RISK_PATTERNS.items()
        }
    
    @property
    def system_prompt(self) -> str:
        return """你是 SalesBoost 系统的【合规审查官】，负责检查销售话术的合规性。

【你的职责】
1. 检测夸大宣传、虚假承诺
2. 检测误导性表述
3. 检测违规词汇
4. 提供安全的替代表述

【高风险类型（必须拦截）】
1. 夸大类 (exaggeration)
   - 绝对化承诺：绝对、100%、肯定、一定
   - 极限词：最好、最强、第一、唯一
   - 无限期承诺：永远、永久、终身

2. 误导类 (misleading)
   - 虚假承诺：稳赚、保本、零风险
   - 隐瞒风险：不可能出问题、绝不会亏损
   - 暗示内幕：内部消息、小道消息

3. 禁止类 (prohibited)
   - 贬低竞品：说竞争对手坏话
   - 商业贿赂：送礼、回扣、好处费
   - 违规操作：私下转账、私人交易

【输出要求】
你必须输出严格的 JSON 格式，包含：
- is_compliant: 是否合规
- risk_flags: 风险标记列表
- blocked: 是否被拦截
- block_reason: 拦截原因
- sanitized_message: 净化后的消息（如果需要）
"""
    
    @property
    def output_schema(self) -> Type[BaseModel]:
        return ComplianceOutput
    
    async def check(
        self,
        message: str,
        stage: SalesStage,
        context: Optional[Dict[str, Any]] = None,
    ) -> ComplianceOutput:
        """
        检查消息合规性
        
        Args:
            message: 待检查消息
            stage: 当前销售阶段
            context: 上下文信息
            
        Returns:
            合规检查结果
        """
        logger.info(f"Compliance check: message='{message[:50]}...'")
        
        risk_flags: List[RiskFlag] = []
        blocked = False
        block_reason = None
        
        # Step 1: 规则引擎检查（高风险）
        for pattern, info in self._compiled_high_patterns.items():
            matches = pattern.findall(message)
            if matches:
                for match in matches:
                    match_text = match if isinstance(match, str) else "".join(match)
                    risk_flags.append(RiskFlag(
                        risk_type=info["risk_type"],
                        original_text=match_text,
                        risk_reason=info["reason"],
                        severity=info["severity"],
                        safe_alternative=info["alternative"],
                    ))
                    blocked = True
        
        # Step 2: 规则引擎检查（中风险）
        for pattern, info in self._compiled_medium_patterns.items():
            matches = pattern.findall(message)
            if matches:
                for match in matches:
                    match_text = match if isinstance(match, str) else "".join(match)
                    risk_flags.append(RiskFlag(
                        risk_type=info["risk_type"],
                        original_text=match_text,
                        risk_reason=info["reason"],
                        severity=info["severity"],
                        safe_alternative=info["alternative"],
                    ))
        
        # Step 3: 如果规则引擎未检测到高风险，使用 LLM 进行深度检查
        if not blocked and len(message) > 20:
            llm_result = await self._llm_deep_check(message, stage)
            if llm_result:
                risk_flags.extend(llm_result)
                # 检查 LLM 结果中是否有高风险
                for flag in llm_result:
                    if flag.severity == "high":
                        blocked = True
                        break
        
        # 设置拦截原因
        if blocked:
            high_risks = [f for f in risk_flags if f.severity == "high"]
            if high_risks:
                block_reason = f"检测到 {len(high_risks)} 个高风险表述：{high_risks[0].risk_reason}"
        
        # 生成净化消息
        sanitized_message = None
        if risk_flags:
            sanitized_message = self._sanitize_message(message, risk_flags)
        
        is_compliant = len(risk_flags) == 0
        
        logger.info(f"Compliance result: compliant={is_compliant}, blocked={blocked}, risks={len(risk_flags)}")
        
        return ComplianceOutput(
            is_compliant=is_compliant,
            risk_flags=risk_flags,
            blocked=blocked,
            block_reason=block_reason,
            sanitized_message=sanitized_message,
        )
    
    async def _llm_deep_check(
        self,
        message: str,
        stage: SalesStage,
    ) -> List[RiskFlag]:
        """
        使用 LLM 进行深度合规检查
        
        Args:
            message: 待检查消息
            stage: 当前阶段
            
        Returns:
            检测到的风险列表
        """
        user_prompt = f"""请检查以下销售话术是否存在合规风险：

【销售阶段】{stage.value}

【待检查内容】
{message}

请仔细分析是否存在：
1. 夸大宣传或虚假承诺
2. 误导性表述
3. 违规词汇或不当表述

如果发现风险，请指出具体问题和建议的替代表述。
如果没有发现风险，请明确说明"未发现合规风险"。"""
        
        try:
            # 使用原始输出进行分析
            raw_result = await self.invoke_raw(user_prompt)
            
            # 解析 LLM 结果
            return self._parse_llm_result(raw_result)
        except Exception as e:
            logger.error(f"LLM deep check failed: {e}")
            return []
    
    def _parse_llm_result(self, raw_result: str) -> List[RiskFlag]:
        """解析 LLM 检查结果"""
        risk_flags = []
        
        # 如果明确表示无风险，返回空列表
        if "未发现" in raw_result and "风险" in raw_result:
            return []
        
        # 简单的关键词检测来判断是否有风险
        risk_keywords = {
            "夸大": ("exaggeration", "medium"),
            "虚假": ("misleading", "high"),
            "误导": ("misleading", "medium"),
            "违规": ("prohibited", "high"),
            "不当": ("prohibited", "medium"),
        }
        
        for keyword, (risk_type, severity) in risk_keywords.items():
            if keyword in raw_result:
                # 提取相关句子作为原因
                sentences = raw_result.split("。")
                for sentence in sentences:
                    if keyword in sentence:
                        risk_flags.append(RiskFlag(
                            risk_type=risk_type,
                            original_text="(LLM 检测)",
                            risk_reason=sentence.strip()[:100],
                            severity=severity,
                            safe_alternative=None,
                        ))
                        break
        
        return risk_flags
    
    def _sanitize_message(
        self,
        message: str,
        risk_flags: List[RiskFlag],
    ) -> str:
        """
        净化消息，替换风险表述
        
        Args:
            message: 原始消息
            risk_flags: 风险标记列表
            
        Returns:
            净化后的消息
        """
        sanitized = message
        
        for flag in risk_flags:
            if flag.safe_alternative and flag.original_text != "(LLM 检测)":
                # 尝试替换原始文本
                sanitized = sanitized.replace(flag.original_text, f"[建议修改: {flag.safe_alternative}]")
        
        return sanitized
    
    def add_custom_rule(
        self,
        pattern: str,
        risk_type: str,
        severity: str,
        reason: str,
        alternative: Optional[str] = None,
    ) -> bool:
        """
        添加自定义合规规则
        
        Args:
            pattern: 正则表达式模式
            risk_type: 风险类型
            severity: 严重程度
            reason: 风险原因
            alternative: 安全替代表述
            
        Returns:
            是否添加成功
        """
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
            info = {
                "risk_type": risk_type,
                "severity": severity,
                "reason": reason,
                "alternative": alternative,
            }
            
            if severity == "high":
                self._compiled_high_patterns[compiled] = info
            else:
                self._compiled_medium_patterns[compiled] = info
            
            logger.info(f"Custom rule added: pattern={pattern}, severity={severity}")
            return True
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            return False
