"""
上下文压缩器 - Context Compression
使用LLM提取最相关的文档片段，减少token消耗
针对金融场景优化：精确提取关键信息（费率、条款、风险提示等）
"""
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class ContextCompressor:
    """
    上下文压缩器
    
    针对金融场景优化：
    - 精确提取关键数字（费率、年费、额度等）
    - 保留合规条款和风险提示
    - 去除冗余描述
    """
    
    def __init__(self, llm_client: Optional[OpenAI] = None):
        """
        初始化上下文压缩器
        
        Args:
            llm_client: OpenAI客户端
        """
        self.llm_client = llm_client
    
    async def compress(
        self,
        query: str,
        documents: List[str],
        max_tokens: int = 500,
        preserve_financial_data: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        压缩文档，只保留最相关的片段
        
        Args:
            query: 查询文本
            documents: 文档列表
            max_tokens: 每个文档的最大token数
            preserve_financial_data: 是否保留金融数据（费率、年费等）
            
        Returns:
            压缩后的文档列表，包含原始内容和压缩内容
        """
        if not self.llm_client:
            # 降级：简单截断
            return self._truncate_fallback(documents, max_tokens)
        
        compressed_docs = []
        
        for doc in documents:
            try:
                compressed = await self._compress_single(
                    query=query,
                    document=doc,
                    max_tokens=max_tokens,
                    preserve_financial_data=preserve_financial_data,
                )
                compressed_docs.append({
                    "original": doc,
                    "compressed": compressed,
                    "compression_ratio": len(compressed) / len(doc) if doc else 1.0,
                })
            except Exception as e:
                logger.error(f"Compression failed for document: {e}")
                # 降级：使用原始文档
                compressed_docs.append({
                    "original": doc,
                    "compressed": doc[:max_tokens * 4],  # 粗略估算：1 token ≈ 4 chars
                    "compression_ratio": 1.0,
                })
        
        return compressed_docs
    
    async def _compress_single(
        self,
        query: str,
        document: str,
        max_tokens: int,
        preserve_financial_data: bool,
    ) -> str:
        """压缩单个文档"""
        # 构建提示词（针对金融场景）
        financial_instruction = ""
        if preserve_financial_data:
            financial_instruction = """
【金融数据保留要求】
必须完整保留以下信息：
- 数字和百分比（费率、年费、额度、利率等）
- 合规条款和风险提示
- 关键日期和期限
- 产品名称和代码
"""
        
        prompt = f"""你是一个金融知识库的上下文压缩助手。请从以下文档中提取与查询最相关的片段。

【查询】
{query}

【原始文档】
{document[:2000]}  # 限制长度

【要求】
1. 只保留与查询直接相关的内容
2. 保持语义完整性，不要截断句子
3. 压缩后的内容应该在 {max_tokens} tokens以内
{financial_instruction}
4. 去除冗余描述和无关信息
5. 保留关键事实和数据

【输出】
直接输出压缩后的内容，不要添加解释。"""

        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "你是一个专业的金融文档压缩助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 低温度保证准确性
                max_tokens=max_tokens * 2,  # 允许一些余量
            )
            
            compressed = response.choices[0].message.content.strip()
            return compressed
            
        except Exception as e:
            logger.error(f"LLM compression failed: {e}")
            return self._truncate_fallback([document], max_tokens)[0]["compressed"]
    
    def _truncate_fallback(
        self,
        documents: List[str],
        max_tokens: int,
    ) -> List[Dict[str, Any]]:
        """降级方案：简单截断"""
        max_chars = max_tokens * 4  # 粗略估算
        
        compressed = []
        for doc in documents:
            if len(doc) > max_chars:
                # 尝试在句子边界截断
                truncated = doc[:max_chars]
                last_period = truncated.rfind("。")
                if last_period > max_chars * 0.8:  # 如果找到的句号不太远
                    truncated = truncated[:last_period + 1]
                compressed.append({
                    "original": doc,
                    "compressed": truncated + "...",
                    "compression_ratio": len(truncated) / len(doc) if doc else 1.0,
                })
            else:
                compressed.append({
                    "original": doc,
                    "compressed": doc,
                    "compression_ratio": 1.0,
                })
        
        return compressed
    
    def extract_financial_entities(self, text: str) -> Dict[str, List[str]]:
        """
        提取金融实体（费率、年费、额度等）
        用于确保压缩时不会丢失关键信息
        """
        import re
        
        entities = {
            "rates": [],      # 费率、利率
            "fees": [],       # 年费、手续费
            "limits": [],     # 额度、限额
            "dates": [],      # 日期、期限
            "products": [],   # 产品名称
        }
        
        # 费率模式（百分比）
        rate_pattern = r'(\d+\.?\d*)\s*%'
        entities["rates"] = re.findall(rate_pattern, text)
        
        # 年费模式
        fee_pattern = r'年费[：:]\s*(\d+[元万]?)'
        entities["fees"] = re.findall(fee_pattern, text)
        
        # 额度模式
        limit_pattern = r'额度[：:]\s*(\d+[元万]?)'
        entities["limits"] = re.findall(limit_pattern, text)
        
        # 日期模式
        date_pattern = r'(\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{2}-\d{2})'
        entities["dates"] = re.findall(date_pattern, text)
        
        # 产品名称（简单模式）
        product_pattern = r'([A-Z]{2,}\d+[A-Z]?|[信用卡|借记卡|理财|基金][\u4e00-\u9fff]+)'
        entities["products"] = re.findall(product_pattern, text)
        
        return entities



