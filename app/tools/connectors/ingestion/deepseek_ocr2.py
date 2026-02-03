"""
DeepSeek-OCR-2 完整集成

DeepSeek-OCR-2 是 2026 年最先进的 OCR 系统，支持：
1. 视觉因果流理解
2. 动态分辨率处理
3. 高质量 Markdown 输出
4. 表格结构保留
5. 手写体识别

部署方式：
1. vLLM 本地部署（推荐）
2. API 调用
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Any, Dict, List, Optional

import httpx
from PIL import Image

logger = logging.getLogger(__name__)


class DeepSeekOCR2Client:
    """
    DeepSeek-OCR-2 客户端

    支持两种部署方式：
    1. 本地 vLLM 部署
    2. 云端 API
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        api_key: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        初始化客户端

        Args:
            base_url: API 基础 URL
            api_key: API 密钥（可选）
            timeout: 超时时间（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def process_image(
        self,
        image: bytes,
        prompt: str = "<image>\n<|grounding|>Convert the document to markdown.",
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """
        处理图片

        Args:
            image: 图片字节
            prompt: 提示词
            max_tokens: 最大 token 数
            temperature: 温度

        Returns:
            提取的 Markdown 文本
        """
        try:
            # 编码图片为 base64
            image_base64 = base64.b64encode(image).decode("utf-8")

            # 构建请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                # vLLM 格式请求
                payload = {
                    "model": "deepseek-ai/deepseek-ocr-2",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }

                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(
                        f"DeepSeek-OCR-2 API error: {response.status_code} - {response.text}"
                    )
                    raise RuntimeError(f"API error: {response.status_code}")

        except Exception as e:
            logger.error(f"DeepSeek-OCR-2 processing failed: {e}")
            raise

    async def process_pdf(
        self,
        pdf_bytes: bytes,
        dpi: int = 300,
        max_pages: Optional[int] = None,
    ) -> str:
        """
        处理 PDF 文档

        Args:
            pdf_bytes: PDF 字节
            dpi: 渲染 DPI
            max_pages: 最大页数（None = 全部）

        Returns:
            提取的 Markdown 文本
        """
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)

            if max_pages:
                total_pages = min(total_pages, max_pages)

            markdown_parts = []

            for page_num in range(total_pages):
                logger.info(f"Processing page {page_num + 1}/{total_pages}")

                page = doc[page_num]

                # 渲染为图片
                pix = page.get_pixmap(dpi=dpi)
                img_bytes = pix.tobytes("png")

                # OCR 处理
                markdown = await self.process_image(img_bytes)

                markdown_parts.append(f"## Page {page_num + 1}\n\n{markdown}")

            doc.close()

            return "\n\n".join(markdown_parts)

        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise

    async def process_with_grounding(
        self,
        image: bytes,
        task: str = "Convert the document to markdown",
    ) -> Dict[str, Any]:
        """
        使用 grounding 模式处理

        Args:
            image: 图片字节
            task: 任务描述

        Returns:
            包含 markdown 和 grounding 信息的字典
        """
        prompt = f"<image>\n<|grounding|>{task}"

        markdown = await self.process_image(image, prompt=prompt)

        return {
            "markdown": markdown,
            "task": task,
            "grounding_enabled": True,
        }

    async def extract_table(self, image: bytes) -> str:
        """
        提取表格

        Args:
            image: 图片字节

        Returns:
            Markdown 格式的表格
        """
        prompt = "<image>\n<|grounding|>Extract all tables from this image and convert them to markdown format."

        return await self.process_image(image, prompt=prompt)

    async def extract_handwriting(self, image: bytes) -> str:
        """
        识别手写体

        Args:
            image: 图片字节

        Returns:
            识别的文本
        """
        prompt = "<image>\n<|grounding|>Recognize all handwritten text in this image."

        return await self.process_image(image, prompt=prompt)


class DeepSeekOCR2Processor:
    """
    DeepSeek-OCR-2 处理器（用于 streaming pipeline）
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        api_key: Optional[str] = None,
    ):
        self.client = DeepSeekOCR2Client(base_url=base_url, api_key=api_key)

    async def process(self, content: bytes, metadata: Dict[str, Any]) -> str:
        """
        处理文档

        Args:
            content: 文件内容
            metadata: 元数据

        Returns:
            提取的 Markdown 文本
        """
        data_type = metadata.get("data_type", "unknown")

        try:
            if data_type == "pdf":
                # 处理 PDF
                return await self.client.process_pdf(content, dpi=300)
            elif data_type == "image":
                # 处理图片
                return await self.client.process_image(content)
            else:
                # 尝试作为图片处理
                return await self.client.process_image(content)

        except Exception as e:
            logger.error(f"DeepSeek-OCR-2 processing failed: {e}")
            # 降级到 Unstructured
            from app.tools.connectors.ingestion.processors import UnstructuredProcessor

            fallback = UnstructuredProcessor()
            return await fallback.process(content, metadata)


# 部署脚本示例
VLLM_DEPLOYMENT_SCRIPT = """
#!/bin/bash

# DeepSeek-OCR-2 vLLM 部署脚本

# 安装 vLLM
pip install vllm

# 启动 vLLM 服务
python -m vllm.entrypoints.openai.api_server \\
    --model deepseek-ai/deepseek-ocr-2 \\
    --host 0.0.0.0 \\
    --port 8001 \\
    --tensor-parallel-size 1 \\
    --dtype auto \\
    --max-model-len 4096

# 或使用 Docker
docker run --gpus all \\
    -p 8001:8000 \\
    -v ~/.cache/huggingface:/root/.cache/huggingface \\
    vllm/vllm-openai:latest \\
    --model deepseek-ai/deepseek-ocr-2 \\
    --dtype auto
"""


# 使用示例
USAGE_EXAMPLE = """
# 使用示例

from app.tools.connectors.ingestion.deepseek_ocr2 import DeepSeekOCR2Client

# 初始化客户端
client = DeepSeekOCR2Client(
    base_url="http://localhost:8001",
    api_key=None,  # 本地部署不需要
)

# 处理图片
with open("document.png", "rb") as f:
    image_bytes = f.read()

markdown = await client.process_image(image_bytes)
print(markdown)

# 处理 PDF
with open("contract.pdf", "rb") as f:
    pdf_bytes = f.read()

markdown = await client.process_pdf(pdf_bytes, dpi=300)
print(markdown)

# 提取表格
with open("table.png", "rb") as f:
    image_bytes = f.read()

table_markdown = await client.extract_table(image_bytes)
print(table_markdown)

# 识别手写体
with open("handwriting.png", "rb") as f:
    image_bytes = f.read()

text = await client.extract_handwriting(image_bytes)
print(text)
"""
