"""
Smart Ingestion Router - Intelligent data processing gateway.

Routes documents to appropriate processing pipelines based on complexity:
- Simple path: Fast, cheap processing for clean data
- Advanced path: Deep processing for complex/dirty data

Philosophy: "Use a scalpel for surgery, not a sledgehammer"
"""
from __future__ import annotations

import io
import logging
import mimetypes
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ProcessingComplexity(str, Enum):
    """Processing complexity levels."""

    LOW = "low"  # Fast path: PyMuPDF, basic text extraction
    MEDIUM = "medium"  # Standard path: Unstructured, basic OCR
    HIGH = "high"  # Advanced path: DeepSeek-OCR-2, Docling
    EXTREME = "extreme"  # Heavy path: Video/Audio processing


class DataType(str, Enum):
    """Data type categories."""

    TEXT = "text"  # Plain text, markdown, code
    PDF = "pdf"  # PDF documents
    IMAGE = "image"  # Images (PNG, JPG, etc.)
    SPREADSHEET = "spreadsheet"  # Excel, CSV
    AUDIO = "audio"  # Audio files
    VIDEO = "video"  # Video files
    ARCHIVE = "archive"  # ZIP, RAR, etc.
    UNKNOWN = "unknown"


@dataclass
class RoutingDecision:
    """Routing decision with reasoning."""

    complexity: ProcessingComplexity
    data_type: DataType
    processor: str  # Which processor to use
    estimated_cost: float  # Estimated processing cost (0-1)
    estimated_time: float  # Estimated time in seconds
    reasoning: str  # Why this route was chosen
    metadata: Dict[str, Any]  # Additional metadata


class ComplexityEvaluator:
    """
    Evaluates document complexity using lightweight heuristics.

    Strategy:
    1. File type detection (cheap)
    2. Size-based filtering (cheap)
    3. Content sampling (cheap)
    4. Pattern matching (cheap)
    5. Only escalate to expensive methods if needed
    """

    def __init__(self):
        # Thresholds (tunable)
        self.pdf_size_threshold = 5 * 1024 * 1024  # 5MB
        self.image_size_threshold = 2 * 1024 * 1024  # 2MB
        self.text_density_threshold = 0.3  # 30% text in image
        self.table_pattern_threshold = 3  # Number of table patterns

    def evaluate_pdf(self, content: bytes, filename: str) -> Tuple[ProcessingComplexity, Dict[str, Any]]:
        """
        Evaluate PDF complexity.

        Fast checks (in order):
        1. File size
        2. Text extractability
        3. Image density
        4. Table complexity
        """
        metadata = {"filename": filename, "size": len(content)}

        # Check 1: Size-based routing
        if len(content) > self.pdf_size_threshold:
            return ProcessingComplexity.HIGH, {
                **metadata,
                "reason": "large_file",
                "size_mb": len(content) / (1024 * 1024),
            }

        # Check 2: Try fast text extraction
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=content, filetype="pdf")
            total_text = ""
            total_images = 0
            total_pages = len(doc)

            # Sample first 3 pages only (cheap)
            sample_pages = min(3, total_pages)

            for page_num in range(sample_pages):
                page = doc[page_num]
                text = page.get_text()
                total_text += text
                total_images += len(page.get_images())

            doc.close()

            # Calculate metrics
            text_length = len(total_text.strip())
            avg_text_per_page = text_length / sample_pages if sample_pages > 0 else 0
            avg_images_per_page = total_images / sample_pages if sample_pages > 0 else 0

            metadata.update(
                {
                    "total_pages": total_pages,
                    "avg_text_per_page": avg_text_per_page,
                    "avg_images_per_page": avg_images_per_page,
                    "sample_text_length": text_length,
                }
            )

            # Decision logic
            if avg_text_per_page < 50:
                # Very little text = likely scanned
                return ProcessingComplexity.HIGH, {
                    **metadata,
                    "reason": "scanned_pdf",
                }

            if avg_images_per_page > 5:
                # Image-heavy PDF
                return ProcessingComplexity.MEDIUM, {
                    **metadata,
                    "reason": "image_heavy",
                }

            # Check for table patterns
            table_indicators = [
                r"\|.*\|",  # Markdown tables
                r"┌.*┐",  # Box drawing
                r"╔.*╗",  # Double box
            ]

            import re

            table_count = sum(
                len(re.findall(pattern, total_text)) for pattern in table_indicators
            )

            if table_count > self.table_pattern_threshold:
                return ProcessingComplexity.MEDIUM, {
                    **metadata,
                    "reason": "complex_tables",
                    "table_indicators": table_count,
                }

            # Clean, text-heavy PDF
            return ProcessingComplexity.LOW, {
                **metadata,
                "reason": "clean_text_pdf",
            }

        except Exception as e:
            logger.warning(f"PDF evaluation failed: {e}")
            # Fallback to medium complexity
            return ProcessingComplexity.MEDIUM, {
                **metadata,
                "reason": "evaluation_failed",
                "error": str(e),
            }

    def evaluate_image(
        self, content: bytes, filename: str
    ) -> Tuple[ProcessingComplexity, Dict[str, Any]]:
        """
        Evaluate image complexity.

        Fast checks:
        1. File size
        2. Image dimensions
        3. Text density (if PIL available)
        """
        metadata = {"filename": filename, "size": len(content)}

        # Check 1: Size
        if len(content) > self.image_size_threshold:
            return ProcessingComplexity.HIGH, {
                **metadata,
                "reason": "large_image",
                "size_mb": len(content) / (1024 * 1024),
            }

        # Check 2: Dimensions and basic analysis
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(content))
            width, height = img.size
            mode = img.mode

            metadata.update(
                {
                    "width": width,
                    "height": height,
                    "mode": mode,
                    "format": img.format,
                }
            )

            # Very small images = likely icons/logos
            if width < 200 or height < 200:
                return ProcessingComplexity.LOW, {
                    **metadata,
                    "reason": "small_icon",
                }

            # Very large images = likely screenshots/scans
            if width > 2000 or height > 2000:
                return ProcessingComplexity.HIGH, {
                    **metadata,
                    "reason": "high_resolution",
                }

            # Check if image is mostly white/empty (cheap heuristic)
            # Sample 100 random pixels
            import random

            sample_size = min(100, width * height)
            pixels = []

            for _ in range(sample_size):
                x = random.randint(0, width - 1)
                y = random.randint(0, height - 1)
                pixel = img.getpixel((x, y))
                pixels.append(pixel)

            # Calculate average brightness
            if mode == "RGB":
                avg_brightness = sum(sum(p) / 3 for p in pixels) / len(pixels)
            elif mode == "L":
                avg_brightness = sum(pixels) / len(pixels)
            else:
                avg_brightness = 128  # Default

            metadata["avg_brightness"] = avg_brightness

            # Very bright = likely empty/whiteboard
            if avg_brightness > 240:
                return ProcessingComplexity.LOW, {
                    **metadata,
                    "reason": "mostly_empty",
                }

            # Medium brightness = likely has content
            return ProcessingComplexity.MEDIUM, {
                **metadata,
                "reason": "standard_image",
            }

        except Exception as e:
            logger.warning(f"Image evaluation failed: {e}")
            return ProcessingComplexity.MEDIUM, {
                **metadata,
                "reason": "evaluation_failed",
                "error": str(e),
            }

    def evaluate_text(
        self, content: bytes, filename: str
    ) -> Tuple[ProcessingComplexity, Dict[str, Any]]:
        """Evaluate plain text complexity (always LOW)."""
        metadata = {"filename": filename, "size": len(content)}

        try:
            text = content.decode("utf-8")
            metadata["length"] = len(text)
            metadata["lines"] = text.count("\n")

            return ProcessingComplexity.LOW, {
                **metadata,
                "reason": "plain_text",
            }
        except UnicodeDecodeError:
            # Not valid UTF-8, might be binary
            return ProcessingComplexity.MEDIUM, {
                **metadata,
                "reason": "encoding_issue",
            }

    def evaluate_spreadsheet(
        self, content: bytes, filename: str
    ) -> Tuple[ProcessingComplexity, Dict[str, Any]]:
        """Evaluate spreadsheet complexity."""
        metadata = {"filename": filename, "size": len(content)}

        # CSV = LOW, Excel = MEDIUM
        if filename.lower().endswith(".csv"):
            return ProcessingComplexity.LOW, {
                **metadata,
                "reason": "simple_csv",
            }
        else:
            return ProcessingComplexity.MEDIUM, {
                **metadata,
                "reason": "excel_file",
            }

    def evaluate_audio(
        self, content: bytes, filename: str
    ) -> Tuple[ProcessingComplexity, Dict[str, Any]]:
        """Evaluate audio complexity."""
        metadata = {"filename": filename, "size": len(content)}

        # Audio always requires transcription = HIGH
        return ProcessingComplexity.HIGH, {
            **metadata,
            "reason": "audio_transcription_required",
        }

    def evaluate_video(
        self, content: bytes, filename: str
    ) -> Tuple[ProcessingComplexity, Dict[str, Any]]:
        """Evaluate video complexity."""
        metadata = {"filename": filename, "size": len(content)}

        # Video = EXTREME (most expensive)
        return ProcessingComplexity.EXTREME, {
            **metadata,
            "reason": "video_processing_required",
        }


class SmartIngestionRouter:
    """
    Smart router that directs documents to appropriate processing pipelines.

    Cost optimization strategy:
    - LOW: PyMuPDF, basic text extraction (~$0.001/doc)
    - MEDIUM: Unstructured, basic OCR (~$0.01/doc)
    - HIGH: DeepSeek-OCR-2, Docling (~$0.10/doc)
    - EXTREME: Video/Audio processing (~$1.00/doc)
    """

    def __init__(self):
        self.evaluator = ComplexityEvaluator()

        # Processor mapping
        self.processors = {
            (DataType.TEXT, ProcessingComplexity.LOW): "text_extractor",
            (DataType.PDF, ProcessingComplexity.LOW): "pymupdf",
            (DataType.PDF, ProcessingComplexity.MEDIUM): "unstructured",
            (DataType.PDF, ProcessingComplexity.HIGH): "deepseek_ocr2",
            (DataType.IMAGE, ProcessingComplexity.LOW): "skip",
            (DataType.IMAGE, ProcessingComplexity.MEDIUM): "basic_ocr",
            (DataType.IMAGE, ProcessingComplexity.HIGH): "deepseek_ocr2",
            (DataType.SPREADSHEET, ProcessingComplexity.LOW): "pandas",
            (DataType.SPREADSHEET, ProcessingComplexity.MEDIUM): "pandas",
            (DataType.AUDIO, ProcessingComplexity.HIGH): "whisper",
            (DataType.VIDEO, ProcessingComplexity.EXTREME): "video_llava",
        }

        # Cost estimates (relative, 0-1 scale)
        self.cost_estimates = {
            ProcessingComplexity.LOW: 0.01,
            ProcessingComplexity.MEDIUM: 0.1,
            ProcessingComplexity.HIGH: 0.5,
            ProcessingComplexity.EXTREME: 1.0,
        }

        # Time estimates (seconds)
        self.time_estimates = {
            ProcessingComplexity.LOW: 1,
            ProcessingComplexity.MEDIUM: 5,
            ProcessingComplexity.HIGH: 30,
            ProcessingComplexity.EXTREME: 300,
        }

    def detect_data_type(self, content: bytes, filename: str) -> DataType:
        """Detect data type from filename and content."""
        # Try MIME type first
        mime_type, _ = mimetypes.guess_type(filename)

        if mime_type:
            if mime_type.startswith("text/"):
                return DataType.TEXT
            elif mime_type == "application/pdf":
                return DataType.PDF
            elif mime_type.startswith("image/"):
                return DataType.IMAGE
            elif mime_type.startswith("audio/"):
                return DataType.AUDIO
            elif mime_type.startswith("video/"):
                return DataType.VIDEO
            elif "spreadsheet" in mime_type or "excel" in mime_type:
                return DataType.SPREADSHEET

        # Fallback to extension
        ext = Path(filename).suffix.lower()

        if ext in [".txt", ".md", ".py", ".js", ".json", ".xml", ".html"]:
            return DataType.TEXT
        elif ext == ".pdf":
            return DataType.PDF
        elif ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"]:
            return DataType.IMAGE
        elif ext in [".csv", ".xlsx", ".xls"]:
            return DataType.SPREADSHEET
        elif ext in [".mp3", ".wav", ".m4a", ".flac"]:
            return DataType.AUDIO
        elif ext in [".mp4", ".avi", ".mov", ".mkv"]:
            return DataType.VIDEO
        elif ext in [".zip", ".rar", ".7z", ".tar", ".gz"]:
            return DataType.ARCHIVE

        return DataType.UNKNOWN

    def route(self, content: bytes, filename: str) -> RoutingDecision:
        """
        Route document to appropriate processor.

        Args:
            content: File content as bytes
            filename: Original filename

        Returns:
            RoutingDecision with processor and reasoning
        """
        # Step 1: Detect data type (cheap)
        data_type = self.detect_data_type(content, filename)

        # Step 2: Evaluate complexity (cheap heuristics)
        if data_type == DataType.PDF:
            complexity, metadata = self.evaluator.evaluate_pdf(content, filename)
        elif data_type == DataType.IMAGE:
            complexity, metadata = self.evaluator.evaluate_image(content, filename)
        elif data_type == DataType.TEXT:
            complexity, metadata = self.evaluator.evaluate_text(content, filename)
        elif data_type == DataType.SPREADSHEET:
            complexity, metadata = self.evaluator.evaluate_spreadsheet(content, filename)
        elif data_type == DataType.AUDIO:
            complexity, metadata = self.evaluator.evaluate_audio(content, filename)
        elif data_type == DataType.VIDEO:
            complexity, metadata = self.evaluator.evaluate_video(content, filename)
        else:
            # Unknown type = medium complexity
            complexity = ProcessingComplexity.MEDIUM
            metadata = {"filename": filename, "size": len(content), "reason": "unknown_type"}

        # Step 3: Select processor
        processor = self.processors.get(
            (data_type, complexity),
            "unstructured",  # Default fallback
        )

        # Step 4: Build decision
        decision = RoutingDecision(
            complexity=complexity,
            data_type=data_type,
            processor=processor,
            estimated_cost=self.cost_estimates[complexity],
            estimated_time=self.time_estimates[complexity],
            reasoning=metadata.get("reason", "default_routing"),
            metadata=metadata,
        )

        logger.info(
            f"Routed {filename} -> {processor} "
            f"(complexity={complexity}, cost={decision.estimated_cost:.3f}, "
            f"time={decision.estimated_time}s, reason={decision.reasoning})"
        )

        return decision

    def get_statistics(self, decisions: List[RoutingDecision]) -> Dict[str, Any]:
        """Get routing statistics for monitoring."""
        if not decisions:
            return {}

        total_cost = sum(d.estimated_cost for d in decisions)
        total_time = sum(d.estimated_time for d in decisions)

        complexity_counts = {}
        processor_counts = {}

        for d in decisions:
            complexity_counts[d.complexity] = complexity_counts.get(d.complexity, 0) + 1
            processor_counts[d.processor] = processor_counts.get(d.processor, 0) + 1

        return {
            "total_documents": len(decisions),
            "total_estimated_cost": total_cost,
            "total_estimated_time": total_time,
            "avg_cost_per_doc": total_cost / len(decisions),
            "avg_time_per_doc": total_time / len(decisions),
            "complexity_distribution": complexity_counts,
            "processor_distribution": processor_counts,
        }
