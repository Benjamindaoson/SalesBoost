"""
增强文档解析器 - 集成 MinerU 处理复杂文档

支持：
- PDF（包括扫描件、复杂布局）
- Word文档
- Excel文件
- PPT文件
- 表格、公式、图像提取
"""
import logging
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import io

logger = logging.getLogger(__name__)

# MinerU支持
try:
    from mineru import MinerU
    HAS_MINERU = True
except ImportError:
    HAS_MINERU = False
    logger.warning("MinerU not installed. Advanced PDF parsing will be disabled.")

# PyMuPDF（降级方案）
try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

# Excel支持
try:
    import openpyxl
    HAS_EXCEL = True
except ImportError:
    HAS_EXCEL = False

# Word支持
try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


class EnhancedDocumentParser:
    """
    增强文档解析器
    
    优先使用MinerU处理复杂PDF，降级到PyMuPDF处理简单PDF。
    支持Excel、Word等格式。
    """
    
    def __init__(self, llm_client=None, use_mineru: bool = True):
        """
        初始化解析器
        
        Args:
            llm_client: LLM客户端（用于实体提取）
            use_mineru: 是否优先使用MinerU（如果可用）
        """
        self.llm_client = llm_client
        self.use_mineru = use_mineru and HAS_MINERU
        
        if self.use_mineru:
            try:
                # 初始化MinerU（使用pipeline后端，速度较快）
                self.mineru = MinerU(backend="pipeline")
                logger.info("MinerU initialized with pipeline backend")
            except Exception as e:
                logger.warning(f"Failed to initialize MinerU: {e}, falling back to PyMuPDF")
                self.use_mineru = False
                self.mineru = None
        else:
            self.mineru = None
    
    def parse_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        解析PDF文档（优先使用MinerU）
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            {
                "text": str,
                "markdown": str,  # MinerU输出的Markdown
                "metadata": Dict,
                "tables": List[Dict],  # 提取的表格
                "images": List[str],  # 图像路径
            }
        """
        if self.use_mineru and self.mineru:
            return self._parse_pdf_with_mineru(pdf_path)
        elif HAS_PYMUPDF:
            return self._parse_pdf_with_pymupdf(pdf_path)
        else:
            raise ValueError("No PDF parser available. Install MinerU or PyMuPDF.")
    
    def _parse_pdf_with_mineru(self, pdf_path: Path) -> Dict[str, Any]:
        """使用MinerU解析PDF"""
        try:
            logger.info(f"Parsing PDF with MinerU: {pdf_path.name}")
            
            # MinerU解析
            result = self.mineru.parse(str(pdf_path))
            
            # 提取文本和Markdown
            text = ""
            markdown = ""
            tables = []
            images = []
            
            if hasattr(result, 'markdown'):
                markdown = result.markdown
                text = self._markdown_to_text(markdown)
            
            if hasattr(result, 'tables'):
                tables = result.tables
            
            if hasattr(result, 'images'):
                images = result.images
            
            return {
                "text": text or markdown,
                "markdown": markdown,
                "metadata": {
                    "page_count": getattr(result, 'page_count', 0),
                    "has_images": len(images) > 0,
                    "has_tables": len(tables) > 0,
                    "parser": "mineru",
                    "format": "pdf",
                },
                "tables": tables,
                "images": images,
            }
        except Exception as e:
            logger.error(f"MinerU parsing failed: {e}, falling back to PyMuPDF")
            if HAS_PYMUPDF:
                return self._parse_pdf_with_pymupdf(pdf_path)
            raise
    
    def _parse_pdf_with_pymupdf(self, pdf_path: Path) -> Dict[str, Any]:
        """使用PyMuPDF解析PDF（降级方案）"""
        logger.info(f"Parsing PDF with PyMuPDF: {pdf_path.name}")
        
        pdf_doc = fitz.open(str(pdf_path))
        pages_text = []
        has_images = False
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            text = page.get_text()
            pages_text.append(text)
            
            if page.get_images():
                has_images = True
        
        full_text = "\n\n".join(pages_text)
        pdf_doc.close()
        
        return {
            "text": full_text,
            "markdown": None,
            "metadata": {
                "page_count": len(pdf_doc),
                "has_images": has_images,
                "has_tables": False,
                "parser": "pymupdf",
                "format": "pdf",
            },
            "tables": [],
            "images": [],
        }
    
    def parse_excel(self, excel_path: Path) -> Dict[str, Any]:
        """解析Excel文件"""
        if not HAS_EXCEL:
            raise ValueError("Excel parsing requires openpyxl. Install with: pip install openpyxl")
        
        logger.info(f"Parsing Excel: {excel_path.name}")
        
        workbook = openpyxl.load_workbook(excel_path, data_only=True)
        text_parts = []
        tables = []
        
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            text_parts.append(f"【{sheet_name}】\n")
            
            # 提取表格数据
            sheet_data = []
            for row in sheet.iter_rows(values_only=True):
                row_data = [str(cell) if cell is not None else "" for cell in row]
                if any(cell.strip() for cell in row_data):
                    sheet_data.append(row_data)
                    text_parts.append("\t".join(row_data))
            
            if sheet_data:
                tables.append({
                    "sheet_name": sheet_name,
                    "data": sheet_data,
                })
            
            text_parts.append("\n")
        
        content = "\n".join(text_parts)
        
        return {
            "text": content,
            "markdown": None,
            "metadata": {
                "sheet_count": len(workbook.sheetnames),
                "table_count": len(tables),
                "parser": "openpyxl",
                "format": "excel",
            },
            "tables": tables,
            "images": [],
        }
    
    def parse_docx(self, docx_path: Path) -> Dict[str, Any]:
        """解析Word文档（.docx）"""
        if not HAS_DOCX:
            raise ValueError("DOCX parsing requires python-docx. Install with: pip install python-docx")
        
        logger.info(f"Parsing DOCX: {docx_path.name}")
        
        doc = Document(str(docx_path))
        text_parts = []
        tables = []
        
        # 提取段落
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        
        # 提取表格
        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = [cell.text for cell in row.cells]
                if any(cell.strip() for cell in row_data):
                    table_data.append(row_data)
                    text_parts.append("\t".join(row_data))
            
            if table_data:
                tables.append({
                    "data": table_data,
                })
        
        content = "\n".join(text_parts)
        
        return {
            "text": content,
            "markdown": None,
            "metadata": {
                "paragraph_count": len([p for p in doc.paragraphs if p.text.strip()]),
                "table_count": len(tables),
                "parser": "python-docx",
                "format": "docx",
            },
            "tables": tables,
            "images": [],
        }
    
    def parse(self, file_path: Path) -> Dict[str, Any]:
        """
        自动识别格式并解析
        
        Args:
            file_path: 文件路径
            
        Returns:
            解析结果
        """
        suffix = file_path.suffix.lower()
        
        if suffix == ".pdf":
            return self.parse_pdf(file_path)
        elif suffix in [".xlsx", ".xls"]:
            return self.parse_excel(file_path)
        elif suffix == ".docx":
            return self.parse_docx(file_path)
        elif suffix == ".txt":
            return self.parse_text(file_path)
        elif suffix == ".md":
            return self.parse_markdown(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    def parse_text(self, file_path: Path) -> Dict[str, Any]:
        """解析纯文本文件"""
        content = file_path.read_text(encoding="utf-8")
        return {
            "text": content,
            "markdown": None,
            "metadata": {
                "line_count": len(content.splitlines()),
                "parser": "text",
                "format": "txt",
            },
            "tables": [],
            "images": [],
        }
    
    def parse_markdown(self, file_path: Path) -> Dict[str, Any]:
        """解析Markdown文件"""
        content = file_path.read_text(encoding="utf-8")
        return {
            "text": content,
            "markdown": content,
            "metadata": {
                "parser": "markdown",
                "format": "md",
            },
            "tables": [],
            "images": [],
        }
    
    def _markdown_to_text(self, markdown: str) -> str:
        """将Markdown转换为纯文本"""
        # 移除Markdown标记
        text = re.sub(r'#{1,6}\s+', '', markdown)  # 标题
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # 粗体
        text = re.sub(r'\*(.+?)\*', r'\1', text)  # 斜体
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # 链接
        text = re.sub(r'```[\s\S]*?```', '', text)  # 代码块
        text = re.sub(r'`(.+?)`', r'\1', text)  # 行内代码
        return text


