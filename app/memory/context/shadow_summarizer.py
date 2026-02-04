import logging
from typing import List, Dict, Optional
import json

from app.infra.gateway.model_gateway import ModelGateway
from app.infra.gateway.schemas import ModelCall, RoutingContext, ModelConfig

logger = logging.getLogger(__name__)

class ShadowSummarizer:
    """
    Asynchronous Context Summarizer.
    Compresses conversation history into key points and extracts assets.
    """
    
    def __init__(self, model_gateway: Optional[ModelGateway] = None):
        self.model_gateway = model_gateway or ModelGateway()
        # Use a cost-effective model for internal tasks
        self.config = ModelConfig(
            provider="siliconflow",
            model_name="deepseek-ai/DeepSeek-V3",
            temperature=0.3
        )

    async def summarize(self, history: List[Dict[str, str]]) -> str:
        """Summarize conversation history."""
        if not history:
            return ""
            
        logger.info("Summarizing conversation history via LLM...")
        
        prompt = f"""
        请对以下销售对话历史进行摘要，保留核心事实、用户异议和当前进度。
        摘要要求简洁、客观。
        
        对话历史：
        {json.dumps(history, ensure_ascii=False)}
        
        摘要：
        """
        
        try:
            call = ModelCall(
                prompt=prompt,
                system_prompt="你是一个专业的销售助手，擅长提炼对话要点。",
                config=self.config
            )
            context = RoutingContext(session_id="internal_task")
            summary = await self.model_gateway.call(call, context)
            return summary.strip()
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return "Unable to generate summary."

    async def extract_pending_items(self, history: List[Dict[str, str]]) -> List[str]:
        """Extract tasks and follow-up items mentioned in the conversation."""
        if not history:
            return []
            
        prompt = f"""
        从以下对话历史中提取所有“待办事项”或“后续跟进事项”。
        如果没有任何待办事项，请返回空列表。
        输出格式：JSON 列表，如 ["事项1", "事项2"]
        
        对话历史：
        {json.dumps(history, ensure_ascii=False)}
        
        待办事项：
        """
        
        try:
            call = ModelCall(
                prompt=prompt,
                system_prompt="你是一个严谨的销售助手，负责追踪待办事项。",
                config=self.config
            )
            context = RoutingContext(session_id="internal_task")
            result = await self.model_gateway.call(call, context)
            
            # Basic JSON extraction
            import re
            match = re.search(r'\[.*\]', result.replace('\n', ''))
            if match:
                return json.loads(match.group())
            return []
        except Exception as e:
            logger.error(f"Pending items extraction failed: {e}")
            return []

shadow_summarizer = ShadowSummarizer()
