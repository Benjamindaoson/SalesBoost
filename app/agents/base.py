"""
Agent 基类
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings

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
    ):
        """
        初始化 Agent
        
        Args:
            model_name: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
        """
        self.model_name = model_name or settings.OPENAI_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        self._llm: Optional[ChatOpenAI] = None
    
    @property
    def llm(self) -> ChatOpenAI:
        """获取 LLM 实例（懒加载）"""
        if self._llm is None:
            self._llm = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=120,  # 增加超时时间以适应慢速模型
                max_retries=3,
            )
        return self._llm
    
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
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", full_system_prompt),
            ("human", user_prompt),
        ])
        
        chain = prompt | self.llm | parser
        
        try:
            result = await chain.ainvoke(variables or {})
            return result
        except Exception as e:
            logger.error(f"Agent invocation failed: {e}")
            raise
    
    async def invoke_raw(
        self,
        user_prompt: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        调用 LLM 获取原始输出
        
        Args:
            user_prompt: 用户提示词
            variables: 模板变量
            
        Returns:
            原始输出字符串
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", user_prompt),
        ])
        
        chain = prompt | self.llm
        
        try:
            result = await chain.ainvoke(variables or {})
            return result.content
        except Exception as e:
            logger.error(f"Agent raw invocation failed: {e}")
            raise
