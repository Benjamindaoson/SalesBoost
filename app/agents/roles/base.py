"""
Agent 基类
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar, List, AsyncGenerator
from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.core.structured_output import parse_model_output
from app.core.llm_context import LLMCallContext
from app.core.llm_routing import build_routing_context
from app.services.model_gateway import model_gateway
from app.schemas.trace import AgentDecision
from app.services.observability import trace_manager

logger = logging.getLogger(__name__)
settings = get_settings()

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    """
    Agent 基类

    所有 Agent 必须：
    1. 定义 system_prompt
    2. 定义输出 Schema (Pydantic Model)
    3. 实现 _build_prompt 方法
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        llm_instance: Optional[Any] = None,
    ):
        """
        初始化 Agent

        Args:
            model_name: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            llm_instance: 外部注入的 LLM 实例 (优先使用)
        """
        self.model_name = model_name or settings.OPENAI_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Deprecated: external LLM injection is ignored to ensure unified routing.
        if llm_instance is not None:
            logger.warning("External LLM injection ignored; unified gateway is enforced.")
        self._llm = None
        self._llm_injected = False

    AGENT_TYPE = "generic"

    @property
    def is_llm_injected(self) -> bool:
        """是否使用了外部注入的 LLM"""
        return self._llm_injected
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """系统提示词"""
        pass
    
    @property
    @abstractmethod
    def output_schema(self) -> Type[BaseModel]:
        """输出 Schema"""
        pass
    
    def get_output_parser(self) -> PydanticOutputParser:
        """获取输出解析器"""
        return PydanticOutputParser(pydantic_object=self.output_schema)
    
    async def invoke_with_parser(
        self,
        user_prompt: str,
        variables: Optional[Dict[str, Any]] = None,
        llm_context: Optional[LLMCallContext] = None,
    ) -> BaseModel:
        """
        调用 LLM 并解析输出
        
        Args:
            user_prompt: 用户提示词
            variables: 模板变量
            
        Returns:
            解析后的输出对象
        """
        parser = self.get_output_parser()
        format_instructions = parser.get_format_instructions()
        
        # 转义 JSON schema 中的花括号，避免被 LangChain 解析为模板变量
        escaped_format_instructions = format_instructions.replace("{", "{{").replace("}", "}}")
        
        # 构建完整提示词
        full_system_prompt = f"{self.system_prompt}\n\n{escaped_format_instructions}"
        
        messages = self._format_messages(full_system_prompt, user_prompt, variables or {})
        call_context = llm_context or LLMCallContext(session_id="default", turn_number=1)

        try:
            llm_result = await self._call_llm(messages, call_context)
            parsed = parse_model_output(llm_result.get("content", ""), self.output_schema)
            self._record_parse(call_context, parsed.success, parsed.error, parsed.attempts)
            if not parsed.success or parsed.data is None:
                raise ValueError(parsed.error or "structured_parse_failed")
            return parsed.data
        except Exception as e:
            logger.error(f"Agent invocation failed: {e}")
            raise
    
    async def invoke_stream_with_parser(
        self,
        user_prompt: str,
        variables: Optional[Dict[str, Any]] = None,
        llm_context: Optional[LLMCallContext] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream output: yields {"type": "token", "content": "..."}
        And finally yields {"type": "result", "data": BaseModel}
        """
        parser = self.get_output_parser()
        format_instructions = parser.get_format_instructions()
        escaped_format_instructions = format_instructions.replace("{", "{{").replace("}", "}}")
        full_system_prompt = f"{self.system_prompt}\n\n{escaped_format_instructions}"
        
        messages = self._format_messages(full_system_prompt, user_prompt, variables or {})
        call_context = llm_context or LLMCallContext(session_id="default", turn_number=1)
        
        stream = await self._call_llm_stream(messages, call_context)
        
        buffer = ""
        separator = "###METADATA###"
        metadata_started = False
        full_content = "" # For logging/fallback
        
        async for chunk in stream:
            full_content += chunk
            
            if metadata_started:
                buffer += chunk
                continue
                
            buffer += chunk
            if separator in buffer:
                parts = buffer.split(separator)
                content_part = parts[0]
                metadata_part = parts[1]
                
                if content_part:
                    yield {"type": "token", "content": content_part}
                
                metadata_started = True
                buffer = metadata_part # Remaining is metadata
            else:
                # To avoid yielding partial separator, we keep a small buffer or just yield?
                # For simplicity, if buffer is short, we yield.
                # If buffer ends with partial separator, we hold?
                # Implementing precise buffering is complex.
                # Heuristic: If we are close to end, we might hold.
                # BUT for now, let's just yield. The user might see "#" briefly.
                # To be safer: yield all except last N chars if they match start of separator.
                
                # Check for partial match at end of buffer
                partial_match_len = 0
                for i in range(1, len(separator)):
                    if buffer.endswith(separator[:i]):
                        partial_match_len = i
                
                if partial_match_len > 0:
                    to_yield = buffer[:-partial_match_len]
                    buffer = buffer[-partial_match_len:]
                    if to_yield:
                        yield {"type": "token", "content": to_yield}
                else:
                    yield {"type": "token", "content": buffer}
                    buffer = ""

        # Stream finished.
        # If metadata_started is True, buffer contains JSON string.
        # If not, maybe the model didn't output separator?
        
        try:
            json_str = buffer.strip()
            if not json_str:
                 # Fallback: maybe model outputted valid JSON without separator (old behavior)?
                 # Or maybe the separator was missing.
                 # Try parsing full_content?
                 if not metadata_started:
                     json_str = full_content
            
            # Clean up code blocks if present
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            json_str = json_str.strip()

            parsed = parse_model_output(json_str, self.output_schema)
            self._record_parse(call_context, parsed.success, parsed.error, parsed.attempts)
            
            if parsed.success and parsed.data:
                yield {"type": "result", "data": parsed.data}
            else:
                logger.error(f"Structured parse failed: {parsed.error}")
                # Yield error or partial data?
                # We can't yield result if it failed.
        except Exception as e:
            logger.error(f"Stream parsing error: {e}")

    async def invoke_raw(
        self,
        user_prompt: str,
        variables: Optional[Dict[str, Any]] = None,
        llm_context: Optional[LLMCallContext] = None,
    ) -> str:
        """
        调用 LLM 获取原始输出
        
        Args:
            user_prompt: 用户提示词
            variables: 模板变量
            
        Returns:
            原始输出字符串
        """
        messages = self._format_messages(self.system_prompt, user_prompt, variables or {})
        call_context = llm_context or LLMCallContext(session_id="default", turn_number=1)

        try:
            llm_result = await self._call_llm(messages, call_context)
            return llm_result.get("content", "")
        except Exception as e:
            logger.error(f"Agent raw invocation failed: {e}")
            raise

    def _format_messages(self, system_prompt: str, user_prompt: str, variables: Dict[str, Any]) -> List[Dict[str, str]]:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt),
        ])
        formatted = prompt.format_messages(**variables)
        messages = []
        for msg in formatted:
            role = "assistant" if msg.type == "ai" else ("user" if msg.type == "human" else "system")
            messages.append({"role": role, "content": msg.content})
        return messages

    async def _call_llm(self, messages: List[Dict[str, str]], call_context: LLMCallContext) -> Dict[str, Any]:
        if not call_context.budget_authorized:
            raise RuntimeError("Budget authorization required for LLM call.")
        routing_context = build_routing_context(self.AGENT_TYPE, call_context)
        return await model_gateway.chat(
            agent_type=self.AGENT_TYPE,
            messages=messages,
            context=routing_context,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            trace_id=call_context.trace_id,
            agent_name=self.__class__.__name__,
            prompt_version=call_context.prompt_version,
        )

    async def _call_llm_stream(self, messages: List[Dict[str, str]], call_context: LLMCallContext):
        if not call_context.budget_authorized:
            raise RuntimeError("Budget authorization required for LLM call.")
        routing_context = build_routing_context(self.AGENT_TYPE, call_context)
        return model_gateway.chat_stream(
            agent_type=self.AGENT_TYPE,
            messages=messages,
            context=routing_context,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            trace_id=call_context.trace_id,
            agent_name=self.__class__.__name__,
            prompt_version=call_context.prompt_version,
        )

    def _record_parse(self, call_context: LLMCallContext, success: bool, error: Optional[str], attempts: List[str]) -> None:
        if not call_context.trace_id:
            return
        trace_manager.record_agent_call(
            call_context.trace_id,
            AgentDecision(
                agent_name=self.__class__.__name__,
                action="structured_parse",
                reasoning="success" if success else "failure",
                prompt_version=call_context.prompt_version,
                metadata={"error": error, "attempts": attempts},
            ),
        )
