"""
DeepSeek-OCR-2 Service

This module provides OCR capabilities using DeepSeek-OCR-2 model via vLLM.

Features:
- PDF to Markdown conversion
- Image to Markdown conversion
- Table extraction
- Handwriting recognition
- Multi-language support (Chinese + English)

Architecture:
    Document → OCRService → vLLM (DeepSeek-OCR-2) → Markdown

Usage:
    from app.tools.connectors.ingestion.ocr_service import OCRService

    ocr = OCRService(vllm_url="http://localhost:8000")
    markdown = await ocr.process_document("path/to/document.pdf")
"""

import base64
import logging
from typing import Optional, List
from pathlib import Path
from enum import Enum

import httpx
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Supported document types"""
    PDF = "pdf"
    IMAGE = "image"
    SCAN = "scan"


class OCRService:
    """
    OCR service using DeepSeek-OCR-2 via vLLM

    DeepSeek-OCR-2 is a multimodal model optimized for:
    - Document understanding
    - Table extraction
    - Handwriting recognition
    - Layout preservation
    """

    def __init__(
        self,
        vllm_url: str = "http://localhost:8000",
        model_name: str = "deepseek-ai/deepseek-ocr-2",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        timeout: int = 120,
    ):
        """
        Initialize OCR service

        Args:
            vllm_url: vLLM server URL
            model_name: Model name (deepseek-ocr-2)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (lower = more deterministic)
            timeout: Request timeout in seconds
        """
        self.vllm_url = vllm_url.rstrip("/")
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

        self.client = httpx.AsyncClient(timeout=timeout)

        logger.info(f"[OCRService] Initialized with vLLM URL: {vllm_url}")

    async def process_document(
        self,
        file_path: str,
        doc_type: Optional[DocumentType] = None,
        extract_tables: bool = True,
        preserve_layout: bool = True
    ) -> str:
        """
        Process document and convert to Markdown

        Args:
            file_path: Path to document file
            doc_type: Document type (auto-detected if None)
            extract_tables: Extract tables as Markdown tables
            preserve_layout: Preserve document layout in Markdown

        Returns:
            Markdown representation of document

        Raises:
            ValueError: If file format is not supported
            RuntimeError: If OCR processing fails
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Auto-detect document type
        if doc_type is None:
            doc_type = self._detect_document_type(path)

        logger.info(f"[OCRService] Processing {doc_type.value} document: {path.name}")

        # Convert to images
        images = await self._document_to_images(path, doc_type)

        # Process each page
        markdown_pages = []
        for i, image_data in enumerate(images):
            logger.info(f"[OCRService] Processing page {i+1}/{len(images)}")

            markdown = await self._process_image(
                image_data,
                extract_tables=extract_tables,
                preserve_layout=preserve_layout
            )
            markdown_pages.append(markdown)

        # Combine pages
        full_markdown = "\n\n---\n\n".join(markdown_pages)

        logger.info(f"[OCRService] Processed {len(images)} pages, {len(full_markdown)} chars")

        return full_markdown

    def _detect_document_type(self, path: Path) -> DocumentType:
        """Detect document type from file extension"""
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return DocumentType.PDF
        elif suffix in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
            return DocumentType.IMAGE
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    async def _document_to_images(
        self,
        path: Path,
        doc_type: DocumentType
    ) -> List[bytes]:
        """
        Convert document to list of images (one per page)

        Returns:
            List of image data (PNG format, base64-ready)
        """
        if doc_type == DocumentType.PDF:
            return await self._pdf_to_images(path)
        elif doc_type == DocumentType.IMAGE:
            # Single image
            with open(path, "rb") as f:
                return [f.read()]
        else:
            raise ValueError(f"Unsupported document type: {doc_type}")

    async def _pdf_to_images(self, pdf_path: Path) -> List[bytes]:
        """Convert PDF pages to images"""
        images = []

        # Open PDF
        doc = fitz.open(pdf_path)

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]

                # Render page to image (300 DPI for good quality)
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))

                # Convert to PNG bytes
                img_data = pix.tobytes("png")
                images.append(img_data)

        finally:
            doc.close()

        return images

    async def _process_image(
        self,
        image_data: bytes,
        extract_tables: bool = True,
        preserve_layout: bool = True
    ) -> str:
        """
        Process single image with DeepSeek-OCR-2

        Args:
            image_data: Image data (PNG/JPEG bytes)
            extract_tables: Extract tables as Markdown
            preserve_layout: Preserve layout in output

        Returns:
            Markdown representation of image content
        """
        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        # Build prompt
        prompt = self._build_ocr_prompt(
            extract_tables=extract_tables,
            preserve_layout=preserve_layout
        )

        # Call vLLM API
        try:
            response = await self.client.post(
                f"{self.vllm_url}/v1/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_b64}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                }
            )

            response.raise_for_status()
            result = response.json()

            # Extract markdown from response
            markdown = result["choices"][0]["message"]["content"]

            return markdown.strip()

        except httpx.HTTPError as e:
            logger.error(f"[OCRService] HTTP error: {e}")
            raise RuntimeError(f"OCR processing failed: {e}")

        except Exception as e:
            logger.error(f"[OCRService] Unexpected error: {e}")
            raise RuntimeError(f"OCR processing failed: {e}")

    def _build_ocr_prompt(
        self,
        extract_tables: bool = True,
        preserve_layout: bool = True
    ) -> str:
        """Build OCR prompt for DeepSeek-OCR-2"""
        prompt_parts = [
            "Convert this document image to Markdown format.",
            "",
            "Requirements:",
            "- Extract all text content accurately",
            "- Maintain proper heading hierarchy (# ## ###)",
            "- Preserve bullet points and numbered lists",
        ]

        if extract_tables:
            prompt_parts.extend([
                "- Convert tables to Markdown table format",
                "- Preserve table structure and alignment",
            ])

        if preserve_layout:
            prompt_parts.extend([
                "- Preserve document layout and structure",
                "- Use appropriate Markdown formatting for emphasis (bold, italic)",
                "- Maintain paragraph breaks",
            ])

        prompt_parts.extend([
            "",
            "Output only the Markdown content, no explanations.",
        ])

        return "\n".join(prompt_parts)

    async def health_check(self) -> bool:
        """
        Check if vLLM server is healthy

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.vllm_url}/health")
            return response.status_code == 200

        except Exception as e:
            logger.error(f"[OCRService] Health check failed: {e}")
            return False

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# ==================== Factory Function ====================

_ocr_service: Optional[OCRService] = None


def get_ocr_service(
    vllm_url: Optional[str] = None,
    force_new: bool = False
) -> OCRService:
    """
    Get or create OCR service instance (singleton)

    Args:
        vllm_url: vLLM server URL (uses config if None)
        force_new: Force create new instance

    Returns:
        OCRService instance
    """
    global _ocr_service

    if _ocr_service is None or force_new:
        from core.config import get_settings
        settings = get_settings()

        url = vllm_url or getattr(settings, "VLLM_OCR_URL", "http://localhost:8000")

        _ocr_service = OCRService(vllm_url=url)

    return _ocr_service
