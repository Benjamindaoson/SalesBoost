"""
Phase 3B Week 7 Day 1-2: TTS (Text-to-Speech) with Emotion Control

核心目标：
1. 实现 TTS 引擎（支持多种后端）
2. 根据销售阶段动态调整语音情感
3. 支持语速、音调、音量控制
4. 实现语音缓存机制

实现日期: 2026-02-02
"""

import logging
import os
import sys
import asyncio
import hashlib
from enum import Enum
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.agents.conversation import SalesState

logger = logging.getLogger(__name__)


class TTSBackend(str, Enum):
    """TTS 后端类型"""
    OPENAI = "openai"
    AZURE = "azure"
    EDGE_TTS = "edge_tts"
    LOCAL = "local"


class VoiceEmotion(str, Enum):
    """语音情感类型"""
    FRIENDLY = "friendly"          # 友好（Opening）
    CURIOUS = "curious"            # 好奇（Discovery）
    CONFIDENT = "confident"        # 自信（Pitch）
    EMPATHETIC = "empathetic"      # 同理心（Objection）
    ENTHUSIASTIC = "enthusiastic"  # 热情（Closing）
    NEUTRAL = "neutral"            # 中性（默认）


@dataclass
class VoiceConfig:
    """语音配置"""
    emotion: VoiceEmotion
    speed: float = 1.0      # 语速 (0.5-2.0)
    pitch: float = 1.0      # 音调 (0.5-2.0)
    volume: float = 1.0     # 音量 (0.0-1.0)
    voice_id: str = "alloy" # 音色 ID


@dataclass
class EmotionProfile:
    """情感档案"""
    name: str
    description: str
    speed: float
    pitch: float
    volume: float
    voice_id: str

    def to_voice_config(self) -> VoiceConfig:
        """转换为语音配置"""
        return VoiceConfig(
            emotion=VoiceEmotion(self.name.lower()),
            speed=self.speed,
            pitch=self.pitch,
            volume=self.volume,
            voice_id=self.voice_id
        )


class EmotionLibrary:
    """情感库"""

    PROFILES = {
        VoiceEmotion.FRIENDLY: EmotionProfile(
            name="friendly",
            description="友好、亲切、温暖",
            speed=1.0,
            pitch=1.1,
            volume=0.9,
            voice_id="alloy"
        ),
        VoiceEmotion.CURIOUS: EmotionProfile(
            name="curious",
            description="好奇、探索、倾听",
            speed=0.95,
            pitch=1.05,
            volume=0.85,
            voice_id="nova"
        ),
        VoiceEmotion.CONFIDENT: EmotionProfile(
            name="confident",
            description="自信、专业、权威",
            speed=1.0,
            pitch=0.95,
            volume=1.0,
            voice_id="onyx"
        ),
        VoiceEmotion.EMPATHETIC: EmotionProfile(
            name="empathetic",
            description="同理心、理解、关怀",
            speed=0.9,
            pitch=1.0,
            volume=0.8,
            voice_id="shimmer"
        ),
        VoiceEmotion.ENTHUSIASTIC: EmotionProfile(
            name="enthusiastic",
            description="热情、兴奋、积极",
            speed=1.1,
            pitch=1.15,
            volume=1.0,
            voice_id="fable"
        ),
        VoiceEmotion.NEUTRAL: EmotionProfile(
            name="neutral",
            description="中性、平稳、标准",
            speed=1.0,
            pitch=1.0,
            volume=0.9,
            voice_id="alloy"
        )
    }

    @classmethod
    def get_profile(cls, emotion: VoiceEmotion) -> EmotionProfile:
        """获取情感档案"""
        return cls.PROFILES.get(emotion, cls.PROFILES[VoiceEmotion.NEUTRAL])

    @classmethod
    def get_emotion_for_sales_state(cls, state: SalesState) -> VoiceEmotion:
        """根据销售阶段获取情感"""
        mapping = {
            SalesState.OPENING: VoiceEmotion.FRIENDLY,
            SalesState.DISCOVERY: VoiceEmotion.CURIOUS,
            SalesState.PITCH: VoiceEmotion.CONFIDENT,
            SalesState.OBJECTION: VoiceEmotion.EMPATHETIC,
            SalesState.CLOSING: VoiceEmotion.ENTHUSIASTIC,
            SalesState.COMPLETED: VoiceEmotion.FRIENDLY,
            SalesState.FAILED: VoiceEmotion.NEUTRAL
        }
        return mapping.get(state, VoiceEmotion.NEUTRAL)


class TTSCache:
    """TTS 缓存"""

    def __init__(self, cache_dir: str = "tts_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        logger.info(f"TTSCache initialized: cache_dir={cache_dir}")

    def _get_cache_key(self, text: str, config: VoiceConfig) -> str:
        """生成缓存键"""
        key_str = f"{text}_{config.emotion}_{config.speed}_{config.pitch}_{config.volume}_{config.voice_id}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, text: str, config: VoiceConfig) -> Optional[bytes]:
        """获取缓存"""
        cache_key = self._get_cache_key(text, config)
        cache_file = self.cache_dir / f"{cache_key}.mp3"

        if cache_file.exists():
            logger.debug(f"Cache hit: {cache_key}")
            return cache_file.read_bytes()

        return None

    def set(self, text: str, config: VoiceConfig, audio_data: bytes):
        """设置缓存"""
        cache_key = self._get_cache_key(text, config)
        cache_file = self.cache_dir / f"{cache_key}.mp3"

        cache_file.write_bytes(audio_data)
        logger.debug(f"Cache set: {cache_key}")

    def clear(self):
        """清空缓存"""
        for file in self.cache_dir.glob("*.mp3"):
            file.unlink()
        logger.info("Cache cleared")


class OpenAITTSEngine:
    """OpenAI TTS 引擎"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            logger.warning("OpenAI API key not found")

        logger.info("OpenAITTSEngine initialized")

    async def synthesize(self, text: str, config: VoiceConfig) -> bytes:
        """合成语音"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            # OpenAI TTS API 参数
            response = await client.audio.speech.create(
                model="tts-1",  # 或 "tts-1-hd" 高质量版本
                voice=config.voice_id,
                input=text,
                speed=config.speed
            )

            # 获取音频数据
            audio_data = b""
            async for chunk in response.iter_bytes():
                audio_data += chunk

            logger.info(f"Synthesized {len(audio_data)} bytes")
            return audio_data

        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            raise


class EdgeTTSEngine:
    """Edge TTS 引擎（免费）"""

    def __init__(self):
        logger.info("EdgeTTSEngine initialized")

    async def synthesize(self, text: str, config: VoiceConfig) -> bytes:
        """合成语音"""
        try:
            import edge_tts

            # Edge TTS 音色映射
            voice_mapping = {
                "alloy": "zh-CN-XiaoxiaoNeural",
                "nova": "zh-CN-XiaoyiNeural",
                "onyx": "zh-CN-YunxiNeural",
                "shimmer": "zh-CN-XiaohanNeural",
                "fable": "zh-CN-YunyangNeural"
            }

            voice = voice_mapping.get(config.voice_id, "zh-CN-XiaoxiaoNeural")

            # 生成语音
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=f"{int((config.speed - 1) * 100):+d}%",
                pitch=f"{int((config.pitch - 1) * 50):+d}Hz",
                volume=f"{int(config.volume * 100):+d}%"
            )

            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            logger.info(f"Synthesized {len(audio_data)} bytes")
            return audio_data

        except Exception as e:
            logger.error(f"Edge TTS error: {e}")

            # 回退：使用默认参数重试
            if config.pitch != 1.0 or config.volume != 1.0:
                logger.warning("Retrying with default parameters")
                default_config = VoiceConfig(
                    emotion=config.emotion,
                    speed=config.speed,
                    pitch=1.0,
                    volume=1.0,
                    voice_id=config.voice_id
                )
                return await self.synthesize(text, default_config)

            raise


class EmotionalTTS:
    """情感 TTS 系统"""

    def __init__(
        self,
        backend: TTSBackend = TTSBackend.OPENAI,
        enable_cache: bool = True,
        cache_dir: str = "tts_cache"
    ):
        self.backend = backend
        self.enable_cache = enable_cache

        # 初始化引擎
        if backend == TTSBackend.OPENAI:
            self.engine = OpenAITTSEngine()
        elif backend == TTSBackend.EDGE_TTS:
            self.engine = EdgeTTSEngine()
        else:
            raise ValueError(f"Unsupported backend: {backend}")

        # 初始化缓存
        self.cache = TTSCache(cache_dir) if enable_cache else None

        logger.info(
            f"EmotionalTTS initialized: backend={backend}, "
            f"cache_enabled={enable_cache}"
        )

    async def synthesize(
        self,
        text: str,
        emotion: Optional[VoiceEmotion] = None,
        sales_state: Optional[SalesState] = None,
        config: Optional[VoiceConfig] = None
    ) -> bytes:
        """合成语音"""

        # 确定情感
        if config is None:
            if emotion is None and sales_state is not None:
                emotion = EmotionLibrary.get_emotion_for_sales_state(sales_state)
            elif emotion is None:
                emotion = VoiceEmotion.NEUTRAL

            profile = EmotionLibrary.get_profile(emotion)
            config = profile.to_voice_config()

        logger.info(
            f"Synthesizing: text_len={len(text)}, emotion={config.emotion}, "
            f"speed={config.speed}, pitch={config.pitch}"
        )

        # 检查缓存
        if self.cache:
            cached_audio = self.cache.get(text, config)
            if cached_audio:
                logger.info("Using cached audio")
                return cached_audio

        # 合成语音
        audio_data = await self.engine.synthesize(text, config)

        # 保存缓存
        if self.cache:
            self.cache.set(text, config, audio_data)

        return audio_data

    async def synthesize_with_state(
        self,
        text: str,
        sales_state: SalesState
    ) -> bytes:
        """根据销售阶段合成语音"""
        return await self.synthesize(text=text, sales_state=sales_state)

    def save_audio(self, audio_data: bytes, filename: str):
        """保存音频文件"""
        filepath = Path(filename)
        filepath.write_bytes(audio_data)
        logger.info(f"Audio saved: {filepath}")


# ============================================================================
# 演示和测试
# ============================================================================

async def demo_emotion_library():
    """演示情感库"""
    print("\n" + "=" * 80)
    print("Emotion Library Demo")
    print("=" * 80)

    print("\nAvailable Emotions:")
    for emotion, profile in EmotionLibrary.PROFILES.items():
        print(f"\n  {emotion.value}:")
        print(f"    Description: {profile.description}")
        print(f"    Speed: {profile.speed}")
        print(f"    Pitch: {profile.pitch}")
        print(f"    Volume: {profile.volume}")
        print(f"    Voice: {profile.voice_id}")

    print("\n\nSales State -> Emotion Mapping:")
    for state in SalesState:
        emotion = EmotionLibrary.get_emotion_for_sales_state(state)
        print(f"  {state.value:12s} -> {emotion.value}")


async def demo_tts_synthesis():
    """演示 TTS 合成"""
    print("\n" + "=" * 80)
    print("TTS Synthesis Demo")
    print("=" * 80)

    # 初始化 TTS（使用 Edge TTS 免费版本）
    tts = EmotionalTTS(
        backend=TTSBackend.EDGE_TTS,
        enable_cache=True
    )

    # 测试文本
    test_cases = [
        (SalesState.OPENING, "您好！我是XX银行的销售顾问，很高兴为您服务。"),
        (SalesState.DISCOVERY, "您目前使用信用卡的主要场景是什么？"),
        (SalesState.PITCH, "我们的白金卡最高额度可达50万，比市面上普通信用卡高出5倍。"),
        (SalesState.OBJECTION, "我理解您的顾虑。实际上，首年免年费，您可以零成本体验。"),
        (SalesState.CLOSING, "那我现在帮您办理，需要您提供一下身份证信息。")
    ]

    output_dir = Path("tts_output")
    output_dir.mkdir(exist_ok=True)

    for i, (state, text) in enumerate(test_cases, 1):
        emotion = EmotionLibrary.get_emotion_for_sales_state(state)

        print(f"\n[Test {i}]")
        print(f"  State: {state.value}")
        print(f"  Emotion: {emotion.value}")
        print(f"  Text: {text}")

        try:
            # 合成语音
            audio_data = await tts.synthesize_with_state(text, state)

            # 保存文件
            filename = output_dir / f"test_{i}_{state.value}_{emotion.value}.mp3"
            tts.save_audio(audio_data, str(filename))

            print(f"  [OK] Saved: {filename}")

        except Exception as e:
            print(f"  [ERROR] {e}")


async def demo_cache_performance():
    """演示缓存性能"""
    print("\n" + "=" * 80)
    print("Cache Performance Demo")
    print("=" * 80)

    tts = EmotionalTTS(
        backend=TTSBackend.EDGE_TTS,
        enable_cache=True
    )

    text = "这是一个测试文本，用于演示缓存性能。"
    state = SalesState.OPENING

    # 第一次合成（无缓存）
    print("\n[First synthesis - no cache]")
    import time
    start = time.time()
    audio1 = await tts.synthesize_with_state(text, state)
    time1 = time.time() - start
    print(f"  Time: {time1:.2f}s")
    print(f"  Size: {len(audio1)} bytes")

    # 第二次合成（有缓存）
    print("\n[Second synthesis - with cache]")
    start = time.time()
    audio2 = await tts.synthesize_with_state(text, state)
    time2 = time.time() - start
    print(f"  Time: {time2:.2f}s")
    print(f"  Size: {len(audio2)} bytes")

    # 性能提升
    speedup = time1 / time2 if time2 > 0 else float('inf')
    print(f"\n  Speedup: {speedup:.1f}x")
    print(f"  Cache hit: {audio1 == audio2}")


async def demo_custom_emotion():
    """演示自定义情感"""
    print("\n" + "=" * 80)
    print("Custom Emotion Demo")
    print("=" * 80)

    tts = EmotionalTTS(
        backend=TTSBackend.EDGE_TTS,
        enable_cache=True
    )

    text = "欢迎使用我们的产品！"

    # 测试不同的语速、音调、音量
    configs = [
        VoiceConfig(VoiceEmotion.NEUTRAL, speed=0.8, pitch=0.9, volume=0.7, voice_id="alloy"),
        VoiceConfig(VoiceEmotion.NEUTRAL, speed=1.0, pitch=1.0, volume=1.0, voice_id="alloy"),
        VoiceConfig(VoiceEmotion.NEUTRAL, speed=1.2, pitch=1.1, volume=1.0, voice_id="alloy"),
    ]

    output_dir = Path("tts_output")
    output_dir.mkdir(exist_ok=True)

    for i, config in enumerate(configs, 1):
        print(f"\n[Config {i}]")
        print(f"  Speed: {config.speed}")
        print(f"  Pitch: {config.pitch}")
        print(f"  Volume: {config.volume}")

        try:
            audio_data = await tts.synthesize(text, config=config)
            filename = output_dir / f"custom_{i}_speed{config.speed}_pitch{config.pitch}.mp3"
            tts.save_audio(audio_data, str(filename))
            print(f"  [OK] Saved: {filename}")
        except Exception as e:
            print(f"  [ERROR] {e}")


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 80)
    print("Phase 3B Week 7 Day 1-2: TTS with Emotion Control")
    print("=" * 80)

    # 1. 演示情感库
    await demo_emotion_library()

    # 2. 演示 TTS 合成
    await demo_tts_synthesis()

    # 3. 演示缓存性能
    await demo_cache_performance()

    # 4. 演示自定义情感
    await demo_custom_emotion()

    print("\n" + "=" * 80)
    print("All demos completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
