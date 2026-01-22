"""
查询扩展器 - Query Expansion
使用LLM生成查询变体，提升检索召回率
"""
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class QueryExpander:
    """
    查询扩展器
    
    使用LLM生成查询变体，支持：
    - 同义词扩展
    - 查询改写
    - 多角度查询生成
    """
    
    def __init__(self, llm_client: Optional[OpenAI] = None):
        """
        初始化查询扩展器
        
        Args:
            llm_client: OpenAI客户端（用于生成查询变体）
        """
        self.llm_client = llm_client
    
    async def expand_query(
        self,
        original_query: str,
        context: Optional[Dict[str, Any]] = None,
        num_variants: int = 3,
    ) -> List[str]:
        """
        扩展查询，生成多个变体
        
        Args:
            original_query: 原始查询
            context: 上下文信息（如销售阶段、场景等）
            num_variants: 生成变体数量
            
        Returns:
            查询变体列表（包含原始查询）
        """
        if not self.llm_client:
            # 降级：返回原始查询
            return [original_query]
        
        try:
            # 构建提示词
            context_str = ""
            if context:
                stage = context.get("stage", "")
                context_str = f"\n【上下文】\n- 销售阶段：{stage}\n"
            
            prompt = f"""你是一个销售知识检索系统的查询优化助手。请为以下查询生成{num_variants}个语义相似但表达不同的查询变体，用于提升检索召回率。

【原始查询】
{original_query}
{context_str}

【要求】
1. 每个变体应该从不同角度表达相同或相似的意图
2. 使用同义词、相关术语、不同表达方式
3. 保持查询的核心语义不变
4. 每个变体应该简洁（10-30字）

【输出格式】
直接输出{num_variants}个查询，每行一个，不要编号，不要其他解释文字。"""

            # 调用LLM
            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "你是一个专业的查询优化助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200,
            )
            
            variants_text = response.choices[0].message.content.strip()
            
            # 解析变体（按行分割）
            variants = [
                v.strip()
                for v in variants_text.split("\n")
                if v.strip() and len(v.strip()) > 5  # 过滤太短的
            ]
            
            # 限制数量
            variants = variants[:num_variants]
            
            # 添加原始查询
            all_queries = [original_query] + variants
            
            logger.info(f"Query expanded: {len(all_queries)} variants generated")
            return all_queries
            
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return [original_query]
    
    def expand_with_synonyms(
        self,
        query: str,
        synonym_dict: Optional[Dict[str, List[str]]] = None,
    ) -> List[str]:
        """
        基于同义词词典扩展查询（无需LLM）
        
        Args:
            query: 原始查询
            synonym_dict: 同义词词典 {词: [同义词列表]}
            
        Returns:
            扩展后的查询列表
        """
        if not synonym_dict:
            return [query]
        
        variants = [query]
        query_words = query.split()
        
        # 替换每个词的同义词
        for word in query_words:
            if word in synonym_dict:
                for synonym in synonym_dict[word]:
                    variant = query.replace(word, synonym)
                    if variant not in variants:
                        variants.append(variant)
        
        return variants[:5]  # 限制数量



