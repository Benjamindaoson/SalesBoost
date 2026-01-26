"""
Unified Multimodal Processor - 统一多模态处理器
支持语音、视觉、文本三模态融合

升级: 从仅文本交互扩展为完整多模态支持
"""
import logging
import time
import base64
from typing import Dict, Any, Optional, List, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
import asyncio

from app.core.config import get_settings
from app.core.interaction_config import get_config_manager

logger = logging.getLogger(__name__)


# ============================================================
# Modality Types
# ============================================================

class ModalityType(str, Enum):
    """模态类型"""
    TEXT = "text"
    VOICE = "voice"
    VISION = "vision"
    HYBRID = "hybrid"


class ContentType(str, Enum):
    """内容类型"""
    # 文本
    PLAIN_TEXT = "text/plain"
    MARKDOWN = "text/markdown"
    JSON = "application/json"

    # 语音
    AUDIO_WAV = "audio/wav"
    AUDIO_MP3 = "audio/mp3"
    AUDIO_WEBM = "audio/webm"

    # 视觉
    IMAGE_PNG = "image/png"
    IMAGE_JPEG = "image/jpeg"
    IMAGE_WEBP = "image/webp"
    VIDEO_MP4 = "video/mp4"


# ============================================================
# Input/Output Models
# ============================================================

class ModalityInput(BaseModel):
    """模态输入"""
    modality: ModalityType
    content_type: ContentType
    data: Union[str, bytes]  # 文本或 base64 编码
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessedContent(BaseModel):
    """处理后的内容"""
    modality: ModalityType
    text_representation: str = Field(..., description="文本表示")
    semantic_embedding: Optional[List[float]] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    entities: List[str] = Field(default_factory=list)
    sentiment: Optional[str] = None
    language: str = "zh"
    processing_time_ms: float = 0.0


class FusedUnderstanding(BaseModel):
    """融合后的理解"""
    unified_text: str = Field(..., description="统一文本表示")
    primary_modality: ModalityType
    modality_contributions: Dict[str, float] = Field(default_factory=dict)
    cross_modal_consistency: float = Field(default=1.0)
    key_information: List[str] = Field(default_factory=list)
    intent: Optional[str] = None
    entities: List[str] = Field(default_factory=list)
    total_processing_time_ms: float = 0.0


# ============================================================
# Modality Processors
# ============================================================

class BaseModalityProcessor(ABC):
    """模态处理器基类"""

    @abstractmethod
    async def process(self, input_data: ModalityInput) -> ProcessedContent:
        """处理输入"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查处理器是否可用"""
        pass


class TextProcessor(BaseModalityProcessor):
    """文本处理器"""

    def __init__(self, llm_client=None, embedding_fn=None):
        self.llm_client = llm_client
        self.embedding_fn = embedding_fn

    async def process(self, input_data: ModalityInput) -> ProcessedContent:
        """处理文本输入"""
        start_time = time.time()

        text = input_data.data if isinstance(input_data.data, str) else input_data.data.decode()

        # 基础处理
        entities = self._extract_entities(text)
        sentiment = self._analyze_sentiment(text)

        # 生成嵌入 (如果可用)
        embedding = None
        if self.embedding_fn:
            try:
                embedding = self.embedding_fn([text])[0]
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}")

        return ProcessedContent(
            modality=ModalityType.TEXT,
            text_representation=text,
            semantic_embedding=embedding,
            confidence=1.0,
            entities=entities,
            sentiment=sentiment,
            language=self._detect_language(text),
            processing_time_ms=(time.time() - start_time) * 1000,
        )

    def is_available(self) -> bool:
        return True

    def _extract_entities(self, text: str) -> List[str]:
        """简单实体提取"""
        entities = []

        # 产品名称
        product_patterns = ["信用卡", "借记卡", "理财产品", "保险", "基金"]
        for pattern in product_patterns:
            if pattern in text:
                entities.append(f"PRODUCT:{pattern}")

        # 金额
        import re
        amounts = re.findall(r'\d+(?:\.\d+)?(?:元|万|亿|%)', text)
        for amount in amounts:
            entities.append(f"AMOUNT:{amount}")

        return entities

    def _analyze_sentiment(self, text: str) -> str:
        """简单情感分析"""
        positive_words = ["好", "满意", "喜欢", "棒", "优秀", "感谢"]
        negative_words = ["差", "不满", "投诉", "问题", "失望", "坑"]

        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"

    def _detect_language(self, text: str) -> str:
        """简单语言检测"""
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        if chinese_chars / max(len(text), 1) > 0.3:
            return "zh"
        return "en"


class VoiceProcessor(BaseModalityProcessor):
    """语音处理器"""

    def __init__(self, model: str = "whisper-1", language: str = "zh"):
        self.model = model
        self.language = language
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化 OpenAI 客户端"""
        try:
            settings = get_settings()
            if settings.OPENAI_API_KEY:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                )
        except Exception as e:
            logger.warning(f"Failed to initialize voice client: {e}")

    async def process(self, input_data: ModalityInput) -> ProcessedContent:
        """处理语音输入"""
        start_time = time.time()

        if not self.client:
            return ProcessedContent(
                modality=ModalityType.VOICE,
                text_representation="[语音处理不可用]",
                confidence=0.0,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            # 解码音频数据
            audio_data = input_data.data
            if isinstance(audio_data, str):
                audio_data = base64.b64decode(audio_data)

            # 使用 Whisper 转录
            # 注意: 需要将字节写入临时文件
            import tempfile
            import os

            suffix = self._get_suffix(input_data.content_type)
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(audio_data)
                temp_path = f.name

            try:
                with open(temp_path, "rb") as audio_file:
                    transcript = self.client.audio.transcriptions.create(
                        model=self.model,
                        file=audio_file,
                        language=self.language,
                    )
                text = transcript.text
            finally:
                os.unlink(temp_path)

            # 分析情感 (从语音特征)
            sentiment = self._analyze_voice_sentiment(input_data.metadata)

            return ProcessedContent(
                modality=ModalityType.VOICE,
                text_representation=text,
                confidence=0.9,
                entities=[],
                sentiment=sentiment,
                language=self.language,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"Voice processing failed: {e}")
            return ProcessedContent(
                modality=ModalityType.VOICE,
                text_representation=f"[语音处理失败: {str(e)[:50]}]",
                confidence=0.0,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def is_available(self) -> bool:
        return self.client is not None

    def _get_suffix(self, content_type: ContentType) -> str:
        """获取文件后缀"""
        suffixes = {
            ContentType.AUDIO_WAV: ".wav",
            ContentType.AUDIO_MP3: ".mp3",
            ContentType.AUDIO_WEBM: ".webm",
        }
        return suffixes.get(content_type, ".wav")

    def _analyze_voice_sentiment(self, metadata: Dict[str, Any]) -> str:
        """分析语音情感 (基于元数据)"""
        # 实际实现需要语音情感分析模型
        # 这里简化为基于元数据
        if metadata.get("speaking_rate", 1.0) > 1.3:
            return "excited"
        elif metadata.get("speaking_rate", 1.0) < 0.7:
            return "calm"
        return "neutral"


class VisionProcessor(BaseModalityProcessor):
    """视觉处理器"""

    def __init__(self, model: str = "gpt-4-vision-preview"):
        self.model = model
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化客户端"""
        try:
            settings = get_settings()
            if settings.OPENAI_API_KEY:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                )
        except Exception as e:
            logger.warning(f"Failed to initialize vision client: {e}")

    async def process(self, input_data: ModalityInput) -> ProcessedContent:
        """处理视觉输入"""
        start_time = time.time()

        if not self.client:
            return ProcessedContent(
                modality=ModalityType.VISION,
                text_representation="[视觉处理不可用]",
                confidence=0.0,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            # 准备图像数据
            image_data = input_data.data
            if isinstance(image_data, bytes):
                image_data = base64.b64encode(image_data).decode()

            # 构建请求
            media_type = input_data.content_type.value
            image_url = f"data:{media_type};base64,{image_data}"

            # 使用 GPT-4V 分析
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请描述这张图片的内容，特别关注与销售场景相关的信息。"
                                        "提取关键实体和情感倾向。以 JSON 格式回复。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=500,
            )

            description = response.choices[0].message.content

            # 解析结果
            entities, sentiment = self._parse_vision_response(description)

            return ProcessedContent(
                modality=ModalityType.VISION,
                text_representation=description,
                confidence=0.85,
                entities=entities,
                sentiment=sentiment,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"Vision processing failed: {e}")
            return ProcessedContent(
                modality=ModalityType.VISION,
                text_representation=f"[视觉处理失败: {str(e)[:50]}]",
                confidence=0.0,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def is_available(self) -> bool:
        return self.client is not None

    def _parse_vision_response(self, response: str) -> Tuple[List[str], str]:
        """解析视觉分析响应"""
        import json

        entities = []
        sentiment = "neutral"

        try:
            # 尝试解析 JSON
            if "{" in response:
                json_str = response[response.index("{"):response.rindex("}") + 1]
                data = json.loads(json_str)
                entities = data.get("entities", [])
                sentiment = data.get("sentiment", "neutral")
        except Exception:
            # 降级: 关键词提取
            if "客户" in response or "顾客" in response:
                entities.append("PERSON:customer")
            if "产品" in response or "商品" in response:
                entities.append("OBJECT:product")

        return entities, sentiment


# ============================================================
# Multimodal Fusion Engine
# ============================================================

class MultimodalFusionEngine:
    """多模态融合引擎"""

    def __init__(self):
        self.text_processor = TextProcessor()
        self.voice_processor = VoiceProcessor()
        self.vision_processor = VisionProcessor()

    async def process_and_fuse(
        self,
        inputs: List[ModalityInput],
    ) -> FusedUnderstanding:
        """处理并融合多模态输入"""
        start_time = time.time()

        if not inputs:
            return FusedUnderstanding(
                unified_text="",
                primary_modality=ModalityType.TEXT,
            )

        # 并行处理所有模态
        processed_contents: List[ProcessedContent] = []

        tasks = []
        for inp in inputs:
            processor = self._get_processor(inp.modality)
            tasks.append(processor.process(inp))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, ProcessedContent):
                processed_contents.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Processing failed: {result}")

        # 融合结果
        fused = self._fuse_contents(processed_contents)
        fused.total_processing_time_ms = (time.time() - start_time) * 1000

        return fused

    def _get_processor(self, modality: ModalityType) -> BaseModalityProcessor:
        """获取模态处理器"""
        if modality == ModalityType.VOICE:
            return self.voice_processor
        elif modality == ModalityType.VISION:
            return self.vision_processor
        return self.text_processor

    def _fuse_contents(self, contents: List[ProcessedContent]) -> FusedUnderstanding:
        """融合多模态内容"""
        if not contents:
            return FusedUnderstanding(
                unified_text="",
                primary_modality=ModalityType.TEXT,
            )

        # 确定主模态 (按置信度)
        primary = max(contents, key=lambda c: c.confidence)

        # 合并文本表示
        text_parts = []
        contributions = {}

        for content in contents:
            if content.text_representation:
                text_parts.append(f"[{content.modality.value}] {content.text_representation}")
                contributions[content.modality.value] = content.confidence

        # 合并实体
        all_entities = []
        for content in contents:
            all_entities.extend(content.entities)
        unique_entities = list(set(all_entities))

        # 计算跨模态一致性
        consistency = self._calculate_consistency(contents)

        # 提取关键信息
        key_info = self._extract_key_information(contents)

        return FusedUnderstanding(
            unified_text="\n".join(text_parts) if len(text_parts) > 1 else (text_parts[0] if text_parts else ""),
            primary_modality=primary.modality,
            modality_contributions=contributions,
            cross_modal_consistency=consistency,
            key_information=key_info,
            entities=unique_entities,
        )

    def _calculate_consistency(self, contents: List[ProcessedContent]) -> float:
        """计算跨模态一致性"""
        if len(contents) <= 1:
            return 1.0

        # 检查情感一致性
        sentiments = [c.sentiment for c in contents if c.sentiment]
        if sentiments:
            unique_sentiments = set(sentiments)
            if len(unique_sentiments) == 1:
                return 1.0
            elif len(unique_sentiments) == 2:
                return 0.7
            else:
                return 0.5

        return 0.8

    def _extract_key_information(self, contents: List[ProcessedContent]) -> List[str]:
        """提取关键信息"""
        key_info = []

        for content in contents:
            # 从实体中提取
            for entity in content.entities[:3]:
                if entity not in key_info:
                    key_info.append(entity)

            # 从文本中提取 (简化)
            text = content.text_representation
            if len(text) > 50:
                key_info.append(text[:50] + "...")

        return key_info[:5]


# ============================================================
# Unified Multimodal Processor (Main Entry)
# ============================================================

class UnifiedMultimodalProcessor:
    """
    统一多模态处理器 - 主入口

    核心能力:
    - 自动检测输入模态
    - 并行处理多模态
    - 语义对齐融合
    - 降级处理
    """

    def __init__(self):
        self.fusion_engine = MultimodalFusionEngine()
        self.config_manager = get_config_manager()

    async def process(
        self,
        text: Optional[str] = None,
        audio_data: Optional[bytes] = None,
        image_data: Optional[bytes] = None,
        content_types: Optional[Dict[str, ContentType]] = None,
    ) -> FusedUnderstanding:
        """
        处理多模态输入

        Args:
            text: 文本输入
            audio_data: 音频数据 (bytes)
            image_data: 图像数据 (bytes)
            content_types: 内容类型映射

        Returns:
            FusedUnderstanding
        """
        inputs = []
        content_types = content_types or {}

        # 检查模态启用状态
        modality_config = self.config_manager.modality

        # 文本输入
        if text and modality_config.text_enabled:
            inputs.append(ModalityInput(
                modality=ModalityType.TEXT,
                content_type=ContentType.PLAIN_TEXT,
                data=text,
            ))

        # 语音输入
        if audio_data and modality_config.voice_enabled:
            inputs.append(ModalityInput(
                modality=ModalityType.VOICE,
                content_type=content_types.get("audio", ContentType.AUDIO_WAV),
                data=base64.b64encode(audio_data).decode(),
            ))

        # 视觉输入
        if image_data and modality_config.vision_enabled:
            inputs.append(ModalityInput(
                modality=ModalityType.VISION,
                content_type=content_types.get("image", ContentType.IMAGE_PNG),
                data=base64.b64encode(image_data).decode(),
            ))

        if not inputs:
            logger.warning("No valid inputs provided")
            return FusedUnderstanding(
                unified_text="",
                primary_modality=ModalityType.TEXT,
            )

        return await self.fusion_engine.process_and_fuse(inputs)

    def get_available_modalities(self) -> Dict[str, bool]:
        """获取可用模态"""
        config = self.config_manager.modality
        return {
            "text": config.text_enabled and self.fusion_engine.text_processor.is_available(),
            "voice": config.voice_enabled and self.fusion_engine.voice_processor.is_available(),
            "vision": config.vision_enabled and self.fusion_engine.vision_processor.is_available(),
        }


# ============================================================
# Factory
# ============================================================

def create_multimodal_processor() -> UnifiedMultimodalProcessor:
    """创建多模态处理器"""
    return UnifiedMultimodalProcessor()
