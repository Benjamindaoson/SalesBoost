"""
Document processors for different complexity levels.

Implements the actual processing logic for each route:
- Fast path: PyMuPDF, basic extraction
- Standard path: Unstructured
- Advanced path: DeepSeek-OCR-2, Whisper, etc.
"""
from __future__ import annotations

import io
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DocumentProcessor(ABC):
    """Base class for document processors."""

    @abstractmethod
    async def process(self, content: bytes, metadata: Dict[str, Any]) -> str:
        """
        Process document and return text.

        Args:
            content: Raw file content
            metadata: Metadata from router

        Returns:
            Extracted text (preferably Markdown)
        """
        pass


class TextExtractor(DocumentProcessor):
    """Fast text extraction for plain text files."""

    async def process(self, content: bytes, metadata: Dict[str, Any]) -> str:
        """Extract text with encoding detection."""
        try:
            # Try UTF-8 first
            return content.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to other encodings
            for encoding in ["gbk", "gb2312", "latin-1"]:
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue

            # Last resort: ignore errors
            return content.decode("utf-8", errors="ignore")


class PyMuPDFProcessor(DocumentProcessor):
    """Fast PDF text extraction using PyMuPDF."""

    async def process(self, content: bytes, metadata: Dict[str, Any]) -> str:
        """Extract text from clean PDFs."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=content, filetype="pdf")
            text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                text_parts.append(f"## Page {page_num + 1}\n\n{text}")

            doc.close()

            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"PyMuPDF processing failed: {e}")
            return f"[Error: Failed to extract text from PDF: {e}]"


class UnstructuredProcessor(DocumentProcessor):
    """Standard processing using Unstructured library."""

    async def process(self, content: bytes, metadata: Dict[str, Any]) -> str:
        """Process with Unstructured."""
        try:
            from unstructured.partition.auto import partition

            # Partition document
            elements = partition(file=io.BytesIO(content))

            # Convert to markdown
            text_parts = []
            for element in elements:
                text_parts.append(str(element))

            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"Unstructured processing failed: {e}")
            # Fallback to PyMuPDF
            fallback = PyMuPDFProcessor()
            return await fallback.process(content, metadata)


class BasicOCRProcessor(DocumentProcessor):
    """
    Basic OCR for simple images using Tesseract.

    Faster and cheaper than DeepSeek-OCR-2, suitable for clean images.
    """

    async def process(self, content: bytes, metadata: Dict[str, Any]) -> str:
        """Process with Tesseract OCR."""
        try:
            import pytesseract
            from PIL import Image

            # Open image
            img = Image.open(io.BytesIO(content))

            # Perform OCR (supports Chinese + English)
            text = pytesseract.image_to_string(img, lang="chi_sim+eng")

            return f"# OCR Result\n\n{text}"

        except Exception as e:
            logger.error(f"Basic OCR processing failed: {e}")
            return f"[Error: Failed to perform OCR: {e}]"


class DeepSeekOCR2Processor(DocumentProcessor):
    """
    Advanced OCR using DeepSeek-OCR-2.

    Uses the full-featured OCRService for document processing.
    """

    def __init__(self, vllm_url: Optional[str] = None):
        self.vllm_url = vllm_url or "http://localhost:8000"
        self._ocr_service = None

    def _get_ocr_service(self):
        """Lazy initialization of OCR service."""
        if self._ocr_service is None:
            from app.tools.connectors.ingestion.ocr_service import OCRService
            self._ocr_service = OCRService(vllm_url=self.vllm_url)
        return self._ocr_service

    async def process(self, content: bytes, metadata: Dict[str, Any]) -> str:
        """Process with DeepSeek-OCR-2 via OCRService."""
        try:
            import tempfile
            from pathlib import Path

            # Save content to temp file
            filename = metadata.get("filename", "document.pdf")
            suffix = Path(filename).suffix or ".pdf"

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(content)
                temp_path = f.name

            try:
                # Process with OCR service
                ocr_service = self._get_ocr_service()
                markdown = await ocr_service.process_document(
                    file_path=temp_path,
                    extract_tables=True,
                    preserve_layout=True
                )

                return markdown

            finally:
                # Clean up temp file
                import os
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"DeepSeek-OCR-2 processing failed: {e}")
            # Fallback to Unstructured
            fallback = UnstructuredProcessor()
            return await fallback.process(content, metadata)


class PandasProcessor(DocumentProcessor):
    """Process spreadsheets with Pandas."""

    async def process(self, content: bytes, metadata: Dict[str, Any]) -> str:
        """Convert spreadsheet to markdown table."""
        try:
            import pandas as pd

            filename = metadata.get("filename", "")

            # Read based on extension
            if filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))

            # Convert to markdown
            markdown = df.to_markdown(index=False)

            return f"# Spreadsheet: {filename}\n\n{markdown}"

        except Exception as e:
            logger.error(f"Pandas processing failed: {e}")
            return f"[Error: Failed to process spreadsheet: {e}]"


class WhisperProcessor(DocumentProcessor):
    """Audio transcription using Whisper."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    async def process(self, content: bytes, metadata: Dict[str, Any]) -> str:
        """Transcribe audio."""
        try:
            import whisper
            import tempfile

            # Load model (cached)
            if self._model is None:
                self._model = whisper.load_model(self.model_size)

            # Save to temp file (Whisper requires file path)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(content)
                temp_path = f.name

            # Transcribe
            result = self._model.transcribe(temp_path, language="zh")  # Chinese

            # Clean up
            import os

            os.unlink(temp_path)

            # Format output
            text = result["text"]
            return f"# Audio Transcription\n\n{text}"

        except Exception as e:
            logger.error(f"Whisper processing failed: {e}")
            return f"[Error: Failed to transcribe audio: {e}]"


class ProcessorFactory:
    """Factory for creating processors."""

    _processors: Dict[str, DocumentProcessor] = {}

    @classmethod
    def get_processor(cls, processor_name: str) -> DocumentProcessor:
        """Get or create processor instance."""
        if processor_name not in cls._processors:
            if processor_name == "text_extractor":
                cls._processors[processor_name] = TextExtractor()
            elif processor_name == "pymupdf":
                cls._processors[processor_name] = PyMuPDFProcessor()
            elif processor_name == "unstructured":
                cls._processors[processor_name] = UnstructuredProcessor()
            elif processor_name == "basic_ocr":
                cls._processors[processor_name] = BasicOCRProcessor()
            elif processor_name == "deepseek_ocr2":
                cls._processors[processor_name] = DeepSeekOCR2Processor()
            elif processor_name == "pandas":
                cls._processors[processor_name] = PandasProcessor()
            elif processor_name == "whisper":
                cls._processors[processor_name] = WhisperProcessor()
            elif processor_name == "skip":
                # Return a no-op processor
                cls._processors[processor_name] = TextExtractor()
            else:
                # Default fallback
                logger.warning(f"Unknown processor: {processor_name}, using unstructured")
                cls._processors[processor_name] = UnstructuredProcessor()

        return cls._processors[processor_name]


async def process_document(
    content: bytes, filename: str, processor_name: str, metadata: Dict[str, Any]
) -> str:
    """
    Process document using specified processor.

    Args:
        content: File content
        filename: Original filename
        processor_name: Processor to use
        metadata: Metadata from router

    Returns:
        Extracted text
    """
    processor = ProcessorFactory.get_processor(processor_name)
    return await processor.process(content, metadata)
