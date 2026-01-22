"""
Quick Suggest Service - MVP 实时辅助服务
生成一句话话术，可直接复制发送
"""
import logging
from typing import List, Dict, Optional, Any
from app.schemas.mvp import IntentLabel, QuickSuggestResponse, ComplianceCheckResponse, RiskLevel
from app.schemas.agent_outputs import RAGOutput, CoachOutput
from app.schemas.fsm import FSMState, SalesStage
from app.agents.coach_agent import CoachAgent
from app.agents.rag_agent import RAGAgent
from app.services.intent_classifier import IntentClassifier

logger = logging.getLogger(__name__)


class QuickSuggestService:
    """
    快速建议服务
    
    核心职责：
    - 生成<=220字符的一句话话术
    - 提供至少2条备用话术
    - 权益类必须带来源追溯
    - 只给"可发的话"，不要教学解释
    - 实时合规/风险检测 (Evaluator-in-the-Loop)
    """
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.coach_agent = CoachAgent()
        self.rag_agent = RAGAgent()
    
    async def generate_suggest(
        self,
        session_id: str,
        last_user_msg: str,
        conversation_history: List[Dict[str, Any]],
        fsm_state: FSMState,
        optional_context: Optional[Dict[str, Any]] = None,
    ) -> QuickSuggestResponse:
        """
        生成快速建议
        
        Args:
            session_id: 会话ID
            last_user_msg: 用户最后一条消息
            conversation_history: 对话历史
            fsm_state: FSM状态
            optional_context: 可选上下文
            
        Returns:
            快速建议响应
        """
        # Step 0: 实时合规检测 (Evaluator-in-the-Loop)
        compliance_check = self._check_compliance_fast(last_user_msg)
        warning_msg = None
        if compliance_check.risk_level != RiskLevel.OK:
            warning_msg = f"风险提示：{compliance_check.reason}"
            if compliance_check.risk_level == RiskLevel.BLOCK:
                # 严重违规，建议直接返回警告，不生成建议（或者生成修正后的建议）
                pass

        # Step 1: 意图分类
        intent_label = self.intent_classifier.classify(last_user_msg, optional_context)
        
        # Step 2: 根据意图生成建议
        response = None
        if intent_label == IntentLabel.BENEFIT_QA:
            response = await self._generate_benefit_qa_suggest(
                last_user_msg, conversation_history, fsm_state
            )
        elif intent_label == IntentLabel.OBJECTION_HANDLING:
            response = await self._generate_objection_suggest(
                last_user_msg, conversation_history, fsm_state
            )
        elif intent_label == IntentLabel.CLOSING_PUSH:
            response = await self._generate_closing_suggest(
                last_user_msg, conversation_history, fsm_state
            )
        else:
            response = await self._generate_generic_suggest(
                last_user_msg, conversation_history, fsm_state
            )
            
        # 注入警告
        if warning_msg:
            response.warning = warning_msg
            
        return response

    def _check_compliance_fast(self, text: str) -> ComplianceCheckResponse:
        """
        快速合规检测 (Regex/Keyword based)
        """
        import re
        risk_level = RiskLevel.OK
        reason = None
        
        # 1. 虚假承诺
        if re.search(r"(一定|百分百|保证|绝对).*收益", text):
            risk_level = RiskLevel.BLOCK
            reason = "严禁承诺收益，请使用'预期'、'历史表现'等合规表述。"
            
        # 2. 诱导办卡
        elif re.search(r"帮我个忙|求你了|凑个业绩", text):
            risk_level = RiskLevel.WARN
            reason = "请避免乞讨式营销，应强调产品价值。"
            
        # 3. 贬低竞品
        elif re.search(r"垃圾|骗子|坑人", text):
            risk_level = RiskLevel.WARN
            reason = "请勿使用过激语言贬低竞品。"

        return ComplianceCheckResponse(
            risk_level=risk_level,
            original=text,
            reason=reason
        )
    
    async def _generate_benefit_qa_suggest(
        self,
        user_msg: str,
        history: List[Dict[str, Any]],
        fsm_state: Any,
    ) -> QuickSuggestResponse:
        """生成权益问答建议（必须带来源）"""
        # RAG 检索权益信息
        rag_result: RAGOutput = await self.rag_agent.retrieve(
            query=user_msg,
            stage=fsm_state.current_stage,
            context=self._build_rag_context(history),
        )
        
        # 提取来源信息
        source_titles = []
        source_snippets = []
        
        if rag_result.retrieved_content:
            for item in rag_result.retrieved_content[:3]:
                source_titles.extend(item.source_citations)
                source_snippets.append(item.content[:100])  # 截取前100字符
        
        # 生成建议话术（短句，可直接发送）
        if rag_result.retrieved_content:
            # 有来源：使用RAG内容生成
            primary_content = rag_result.retrieved_content[0].content
            suggested_reply = self._truncate_to_220_chars(primary_content)
            
            # 生成备用话术
            alt_replies = []
            for item in rag_result.retrieved_content[1:3]:
                alt = self._truncate_to_220_chars(item.content)
                if alt and alt != suggested_reply:
                    alt_replies.append(alt)
            
            # 如果备用不足2条，生成变体
            while len(alt_replies) < 2:
                alt_replies.append(self._generate_variant(suggested_reply))
            
            confidence = 0.85 if source_titles else 0.6
        else:
            # 无来源：降级回答
            suggested_reply = "关于权益详情，建议您查看官方规则或联系客服确认，以确保信息准确。"
            alt_replies = [
                "具体的权益信息，我建议您查看我们的官方说明，这样更准确。",
                "为了确保信息的准确性，建议您通过官方渠道查询最新的权益详情。",
            ]
            confidence = 0.5
        
        return QuickSuggestResponse(
            intent_label=IntentLabel.BENEFIT_QA,
            suggested_reply=suggested_reply,
            alt_replies=alt_replies[:2],
            confidence=confidence,
            evidence={
                "source_titles": source_titles[:3],
                "source_snippets": source_snippets[:3],
            } if source_titles else None,
        )
    
    async def _generate_objection_suggest(
        self,
        user_msg: str,
        history: List[Dict[str, Any]],
        fsm_state: Any,
    ) -> QuickSuggestResponse:
        """生成异议处理建议"""
        # 使用 Coach Agent 生成建议
        # 注意：这里需要NPC回复，暂时使用历史中的最后一条NPC消息
        npc_response = ""
        for msg in reversed(history):
            if msg.get("role") == "npc":
                npc_response = msg.get("content", "")
                break
        
        # 如果没有NPC回复，使用默认
        if not npc_response:
            npc_response = "客户提出了异议"
        
        # 调用 Coach Agent（但需要调整输出格式）
        coach_result: CoachOutput = await self.coach_agent.generate_advice(
            user_message=user_msg,
            npc_response=npc_response,
            conversation_history=history,
            fsm_state=fsm_state,
            rag_content=RAGOutput(retrieved_content=[], query_understanding=""),
            compliance_result=None,  # 这里不检查合规
            strategy_analysis=None,
        )[0]
        
        # 提取并格式化建议（短句）
        suggested_reply = self._truncate_to_220_chars(coach_result.example_utterance)
        
        # 生成备用话术
        alt_replies = [
            self._generate_variant(suggested_reply),
            self._truncate_to_220_chars(coach_result.suggestion),
        ]
        
        return QuickSuggestResponse(
            intent_label=IntentLabel.OBJECTION_HANDLING,
            suggested_reply=suggested_reply,
            alt_replies=alt_replies,
            confidence=coach_result.confidence,
        )
    
    async def _generate_closing_suggest(
        self,
        user_msg: str,
        history: List[Dict[str, Any]],
        fsm_state: Any,
    ) -> QuickSuggestResponse:
        """生成推进成交建议"""
        # 识别推进时机，生成推进话术
        suggested_reply = "好的，我现在就帮您办理。请确认一下您的个人信息是否正确？"
        alt_replies = [
            "太好了！我现在为您提交申请，预计3-5个工作日可以完成。",
            "没问题，我马上为您处理。您还有其他需要了解的吗？",
        ]
        
        return QuickSuggestResponse(
            intent_label=IntentLabel.CLOSING_PUSH,
            suggested_reply=suggested_reply,
            alt_replies=alt_replies,
            confidence=0.8,
        )
    
    async def _generate_generic_suggest(
        self,
        user_msg: str,
        history: List[Dict[str, Any]],
        fsm_state: Any,
    ) -> QuickSuggestResponse:
        """生成通用建议"""
        suggested_reply = "我理解您的想法，能否再详细说说您的具体需求？"
        alt_replies = [
            "好的，我明白了。让我为您介绍一下相关的信息。",
            "没问题，我会根据您的需求为您提供最合适的方案。",
        ]
        
        return QuickSuggestResponse(
            intent_label=IntentLabel.OTHER,
            suggested_reply=suggested_reply,
            alt_replies=alt_replies,
            confidence=0.6,
        )
    
    def _truncate_to_220_chars(self, text: str) -> str:
        """截断到220字符，保持句子完整"""
        if len(text) <= 220:
            return text
        
        # 找到最后一个句号/问号/感叹号
        for i in range(219, max(0, 200), -1):
            if text[i] in "。！？":
                return text[:i+1]
        
        # 如果没找到，截断到220字符
        return text[:220]
    
    def _generate_variant(self, text: str) -> str:
        """生成变体话术"""
        # 简单的变体生成（实际可以用模板）
        variants = {
            "我理解": "我明白",
            "您": "你",
            "可以": "能够",
            "现在": "马上",
        }
        
        result = text
        for old, new in variants.items():
            if old in result:
                result = result.replace(old, new, 1)
                break
        
        return result if result != text else text + "（变体）"
    
    def _build_rag_context(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建 RAG 上下文"""
        return {
            "conversation_history": history,
        }

