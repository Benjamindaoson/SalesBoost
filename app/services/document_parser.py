"""
文档解析与结构化萃取服务
支持 PDF、Markdown、TXT 等格式，并提取实体和标签
"""
import logging
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import io

logger = logging.getLogger(__name__)

# 尝试导入 PDF 解析库
try:
    import fitz  # PyMuPDF
    HAS_PDF_SUPPORT = True
except ImportError:
    HAS_PDF_SUPPORT = False
    logger.warning("PyMuPDF not installed. PDF parsing will be disabled.")


class DocumentParser:
    """文档解析器"""
    
    def __init__(self, llm_client=None):
        """
        初始化解析器
        
        Args:
            llm_client: LLM客户端（用于实体提取）
        """
        self.llm_client = llm_client
    
    def parse_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        解析 PDF 文档
        
        Returns:
            {
                "text": str,
                "metadata": {
                    "page_count": int,
                    "has_images": bool,
                    ...
                }
            }
        """
        if not HAS_PDF_SUPPORT:
            raise ValueError("PDF parsing requires PyMuPDF. Install with: pip install pymupdf")
        
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages_text = []
            has_images = False
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                text = page.get_text()
                pages_text.append(text)
                
                # 检查是否有图片
                if page.get_images():
                    has_images = True
            
            full_text = "\n\n".join(pages_text)
            pdf_doc.close()
            
            return {
                "text": full_text,
                "metadata": {
                    "page_count": len(pdf_doc),
                    "has_images": has_images,
                    "format": "pdf"
                }
            }
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            raise ValueError(f"Failed to parse PDF: {e}")
    
    def parse_markdown(self, content: str) -> Dict[str, Any]:
        """解析 Markdown 文档"""
        return {
            "text": content,
            "metadata": {
                "format": "markdown",
                "has_code_blocks": "```" in content,
            }
        }
    
    def parse_text(self, content: str) -> Dict[str, Any]:
        """解析纯文本"""
        return {
            "text": content,
            "metadata": {
                "format": "text",
                "line_count": len(content.splitlines()),
            }
        }
    
    def parse(self, content: bytes, filename: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        自动识别格式并解析
        
        Args:
            content: 文件内容（字节）
            filename: 文件名
            content_type: MIME类型（可选）
        """
        # 根据文件扩展名或内容类型判断
        ext = Path(filename).suffix.lower()
        
        if ext == ".pdf" or content_type == "application/pdf":
            return self.parse_pdf(content)
        elif ext in [".md", ".markdown"] or content_type == "text/markdown":
            return self.parse_markdown(content.decode("utf-8"))
        else:
            # 默认按文本处理
            try:
                text_content = content.decode("utf-8")
                return self.parse_text(text_content)
            except UnicodeDecodeError:
                raise ValueError(f"Unsupported file format: {filename}")


class EntityExtractor:
    """实体和标签提取器（使用 LLM）"""
    
    def __init__(self, llm_client):
        """
        初始化提取器
        
        Args:
            llm_client: LLM客户端（需要支持结构化输出）
        """
        self.llm_client = llm_client
    
    async def extract_entities_and_tags(
        self,
        text: str,
        doc_type: str = "knowledge"
    ) -> Dict[str, Any]:
        """
        从文档中提取结构化信息
        
        Returns:
            {
                "entities": List[str],  # 关键实体（产品名、概念等）
                "tags": List[str],      # 标签（主题、类别）
                "summary": str,         # 摘要
                "key_points": List[str], # 关键要点
                "topics": List[str],    # 主题列表
            }
        """
        if not self.llm_client:
            # 降级：使用简单的关键词提取
            return self._fallback_extraction(text)
        
        prompt = f"""请从以下销售知识文档中提取结构化信息：

【文档类型】{doc_type}
【文档内容】
{text[:3000]}  # 限制长度避免token过多

请提取以下信息（JSON格式）：
1. entities: 关键实体列表（产品名、功能、概念等，最多10个）
2. tags: 标签列表（主题、类别，最多8个）
3. summary: 文档摘要（50-100字）
4. key_points: 关键要点列表（3-5条）
5. topics: 主题列表（销售阶段、场景等，最多5个）

输出格式：
{{
    "entities": ["实体1", "实体2"],
    "tags": ["标签1", "标签2"],
    "summary": "摘要文本",
    "key_points": ["要点1", "要点2"],
    "topics": ["主题1", "主题2"]
}}"""

        try:
            # 调用 LLM（这里假设有 invoke_raw 方法）
            if hasattr(self.llm_client, 'invoke_raw'):
                response = await self.llm_client.invoke_raw(prompt)
            else:
                # 使用 OpenAI 客户端
                from openai import OpenAI
                if isinstance(self.llm_client, OpenAI):
                    response_obj = self.llm_client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"}
                    )
                    response = response_obj.choices[0].message.content
                else:
                    return self._fallback_extraction(text)
            
            # 解析 JSON
            import json
            # 提取 JSON（可能包含markdown代码块）
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                extracted = json.loads(json_match.group())
                return {
                    "entities": extracted.get("entities", []),
                    "tags": extracted.get("tags", []),
                    "summary": extracted.get("summary", ""),
                    "key_points": extracted.get("key_points", []),
                    "topics": extracted.get("topics", []),
                }
            else:
                return self._fallback_extraction(text)
                
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return self._fallback_extraction(text)
    
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """降级提取：使用简单的关键词和模式匹配"""
        # 提取可能的实体（大写词、引号内容）
        entities = []
        tags = []
        
        # 提取引号内容
        quoted = re.findall(r'["""]([^"""]+)["""]', text)
        entities.extend(quoted[:5])
        
        # 提取大写词（可能是产品名）
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', text)
        entities.extend(list(set(capitalized))[:5])
        
        # 简单的标签提取（基于关键词）
        keyword_tags = {
            "产品介绍": ["产品", "功能", "特性"],
            "异议处理": ["异议", "反对", "顾虑"],
            "成交技巧": ["成交", "签约", "购买"],
            "客户沟通": ["沟通", "对话", "交流"],
        }
        
        for tag, keywords in keyword_tags.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)
        
        # 生成简单摘要
        sentences = text.split("。")
        summary = "。".join(sentences[:3]) + "。" if len(sentences) > 3 else text[:100]
        
        return {
            "entities": list(set(entities))[:10],
            "tags": tags[:8],
            "summary": summary[:200],
            "key_points": sentences[:5],
            "topics": tags[:5],
        }


class DocumentProcessor:
    """文档处理管道：解析 + 提取 + 分块"""
    
    def __init__(self, llm_client=None):
        self.parser = DocumentParser(llm_client)
        self.extractor = EntityExtractor(llm_client) if llm_client else None
    
    async def process_document(
        self,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
        doc_type: str = "knowledge",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> Dict[str, Any]:
        """
        完整处理文档：解析 -> 提取 -> 分块
        
        Returns:
            {
                "chunks": List[Dict],  # 文档块列表
                "metadata": Dict,      # 文档元数据
                "entities": List[str], # 实体列表
                "tags": List[str],     # 标签列表
                "summary": str,        # 摘要
            }
        """
        # 1. 解析文档
        parsed = self.parser.parse(content, filename, content_type)
        text = parsed["text"]
        metadata = parsed["metadata"]
        
        # 2. 提取实体和标签
        extraction_result = {}
        if self.extractor:
            extraction_result = await self.extractor.extract_entities_and_tags(text, doc_type)
        else:
            extraction_result = self.extractor._fallback_extraction(text) if self.extractor else {}
        
        # 3. 文档分块（用于向量存储）
        chunks = self._chunk_text(text, chunk_size, chunk_overlap)
        
        return {
            "chunks": chunks,
            "metadata": {
                **metadata,
                **extraction_result,
                "filename": filename,
                "doc_type": doc_type,
                "chunk_count": len(chunks),
            },
            "entities": extraction_result.get("entities", []),
            "tags": extraction_result.get("tags", []),
            "summary": extraction_result.get("summary", ""),
            "key_points": extraction_result.get("key_points", []),
            "topics": extraction_result.get("topics", []),
        }
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        将文本分块（按句子边界，避免截断）
        
        Args:
            text: 原始文本
            chunk_size: 每块的目标字符数
            chunk_overlap: 块之间的重叠字符数
            
        Returns:
            块列表，每个块包含 content 和 metadata
        """
        # 按句子分割
        sentences = re.split(r'[。！？\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > chunk_size and current_chunk:
                # 保存当前块
                chunk_text = "。".join(current_chunk)
                chunks.append({
                    "content": chunk_text,
                    "metadata": {
                        "chunk_index": len(chunks),
                        "char_count": len(chunk_text),
                    }
                })
                
                # 保留重叠部分
                overlap_text = "。".join(current_chunk[-2:]) if len(current_chunk) >= 2 else current_chunk[-1]
                current_chunk = [overlap_text] if len(overlap_text) < chunk_overlap else []
                current_length = len(overlap_text) if current_chunk else 0
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # 添加最后一个块
        if current_chunk:
            chunk_text = "。".join(current_chunk)
            chunks.append({
                "content": chunk_text,
                "metadata": {
                    "chunk_index": len(chunks),
                    "char_count": len(chunk_text),
                }
            })
        
        return chunks


