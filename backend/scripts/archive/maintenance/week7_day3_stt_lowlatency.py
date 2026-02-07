"""
Phase 3B Week 7 Day 3-4: STT (Speech-to-Text) with Low Latency

核心目标：
1. 实现 STT 引擎（支持多种后端）
2. 实现流式识别（低延迟）
3. 支持实时转写和最终结果
4. 集成 VAD (Voice Activity Detection)

实现日期: 2026-02-02
"""

import logging
import os
import sys
import asyncio
import wave
from enum import Enum
from typing import Dict, Optional, Any, List, Callable
from dataclasses import dataclass
from pathlib import Path
import time

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


class STTBackend(str, Enum):
    """STT 后端类型"""
    OPENAI = "openai"
    AZURE = "azure"
    WHISPER_LOCAL = "whisper_local"
    FASTER_WHISPER = "faster_whisper"


class TranscriptionType(str, Enum):
    """转写类型"""
    PARTIAL = "partial"  # 部分结果（实时）
    FINAL = "final"      # 最终结果


@dataclass
class TranscriptionResult:
    """转写结果"""
    text: str
    type: TranscriptionType
    confidence: float = 1.0
    timestamp: float = 0.0
    duration: float = 0.0
    language: str = "zh"


@dataclass
class AudioConfig:
    """音频配置"""
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2  # 16-bit
    chunk_size: int = 1024


class OpenAISTTEngine:
    """OpenAI STT 引擎"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            logger.warning("OpenAI API key not found")

        logger.info("OpenAISTTEngine initialized")

    async def transcribe(
        self,
        audio_file: str,
        language: str = "zh",
        prompt: Optional[str] = None
    ) -> TranscriptionResult:
        """转写音频文件"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            start_time = time.time()

            with open(audio_file, "rb") as f:
                response = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language=language,
                    prompt=prompt,
                    response_format="verbose_json"
                )

            duration = time.time() - start_time

            logger.info(f"Transcribed in {duration:.2f}s: {response.text}")

            return TranscriptionResult(
                text=response.text,
                type=TranscriptionType.FINAL,
                confidence=1.0,
                timestamp=start_time,
                duration=duration,
                language=language
            )

        except Exception as e:
            logger.error(f"OpenAI STT error: {e}")
            raise


class FasterWhisperEngine:
    """Faster Whisper 引擎（本地，低延迟）"""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None

        logger.info(
            f"FasterWhisperEngine initialized: model={model_size}, "
            f"device={device}, compute_type={compute_type}"
        )

    def _load_model(self):
        """加载模型"""
        if self.model is None:
            try:
                from faster_whisper import WhisperModel

                logger.info(f"Loading Faster Whisper model: {self.model_size}")
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
                logger.info("Model loaded successfully")

            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise

    async def transcribe(
        self,
        audio_file: str,
        language: str = "zh",
        beam_size: int = 5
    ) -> TranscriptionResult:
        """转写音频文件"""
        try:
            self._load_model()

            start_time = time.time()

            # Faster Whisper 是同步的，在线程池中运行
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(
                    audio_file,
                    language=language,
                    beam_size=beam_size,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
            )

            # 合并所有片段
            text = " ".join([segment.text for segment in segments])

            duration = time.time() - start_time

            logger.info(f"Transcribed in {duration:.2f}s: {text}")

            return TranscriptionResult(
                text=text,
                type=TranscriptionType.FINAL,
                confidence=1.0,
                timestamp=start_time,
                duration=duration,
                language=info.language
            )

        except Exception as e:
            logger.error(f"Faster Whisper error: {e}")
            raise

    async def transcribe_stream(
        self,
        audio_file: str,
        language: str = "zh",
        callback: Optional[Callable[[TranscriptionResult], None]] = None
    ):
        """流式转写（逐段返回）"""
        try:
            self._load_model()

            start_time = time.time()

            # 流式处理
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(
                    audio_file,
                    language=language,
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
            )

            # 逐段返回
            for segment in segments:
                result = TranscriptionResult(
                    text=segment.text,
                    type=TranscriptionType.PARTIAL,
                    confidence=1.0,
                    timestamp=start_time + segment.start,
                    duration=segment.end - segment.start,
                    language=info.language
                )

                if callback:
                    callback(result)

                # 模拟流式延迟
                await asyncio.sleep(0.1)

            logger.info("Stream transcription completed")

        except Exception as e:
            logger.error(f"Faster Whisper stream error: {e}")
            raise


class VADDetector:
    """Voice Activity Detection (VAD) 检测器"""

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 3
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.aggressiveness = aggressiveness
        self.vad = None

        logger.info(
            f"VADDetector initialized: sample_rate={sample_rate}, "
            f"frame_duration_ms={frame_duration_ms}, aggressiveness={aggressiveness}"
        )

    def _load_vad(self):
        """加载 VAD"""
        if self.vad is None:
            try:
                import webrtcvad
                self.vad = webrtcvad.Vad(self.aggressiveness)
                logger.info("VAD loaded successfully")
            except ImportError:
                logger.warning("webrtcvad not installed, VAD disabled")
                logger.warning("Install with: pip install webrtcvad")
                self.vad = None
            except Exception as e:
                logger.error(f"Failed to load VAD: {e}")
                raise

    def is_speech(self, audio_frame: bytes) -> bool:
        """检测是否为语音"""
        self._load_vad()

        if self.vad is None:
            logger.warning("VAD not available")
            return True  # 假设所有帧都是语音

        try:
            return self.vad.is_speech(audio_frame, self.sample_rate)
        except Exception as e:
            logger.error(f"VAD detection error: {e}")
            return False

    def detect_speech_segments(
        self,
        audio_file: str,
        padding_duration_ms: int = 300
    ) -> List[tuple]:
        """检测语音片段"""
        self._load_vad()

        try:
            # 读取音频文件
            with wave.open(audio_file, 'rb') as wf:
                sample_rate = wf.getframerate()
                num_channels = wf.getnchannels()
                sample_width = wf.getsampwidth()

                if sample_rate != self.sample_rate:
                    logger.warning(
                        f"Sample rate mismatch: expected {self.sample_rate}, "
                        f"got {sample_rate}"
                    )

                # 计算帧大小
                frame_size = int(sample_rate * self.frame_duration_ms / 1000)
                frame_bytes = frame_size * sample_width * num_channels

                # 读取所有帧
                frames = []
                while True:
                    frame = wf.readframes(frame_size)
                    if len(frame) < frame_bytes:
                        break
                    frames.append(frame)

            # 检测语音
            speech_frames = []
            for i, frame in enumerate(frames):
                is_speech = self.is_speech(frame)
                speech_frames.append((i, is_speech))

            # 合并连续的语音片段
            segments = []
            start_frame = None

            for i, is_speech in speech_frames:
                if is_speech and start_frame is None:
                    start_frame = i
                elif not is_speech and start_frame is not None:
                    segments.append((start_frame, i))
                    start_frame = None

            if start_frame is not None:
                segments.append((start_frame, len(speech_frames)))

            # 转换为时间戳
            frame_duration_s = self.frame_duration_ms / 1000
            time_segments = [
                (start * frame_duration_s, end * frame_duration_s)
                for start, end in segments
            ]

            logger.info(f"Detected {len(time_segments)} speech segments")
            return time_segments

        except Exception as e:
            logger.error(f"VAD segment detection error: {e}")
            return []


class LowLatencySTT:
    """低延迟 STT 系统"""

    def __init__(
        self,
        backend: STTBackend = STTBackend.FASTER_WHISPER,
        enable_vad: bool = True,
        audio_config: Optional[AudioConfig] = None
    ):
        self.backend = backend
        self.enable_vad = enable_vad
        self.audio_config = audio_config or AudioConfig()

        # 初始化引擎
        if backend == STTBackend.OPENAI:
            self.engine = OpenAISTTEngine()
        elif backend == STTBackend.FASTER_WHISPER:
            self.engine = FasterWhisperEngine(
                model_size="base",
                device="cpu",
                compute_type="int8"
            )
        else:
            raise ValueError(f"Unsupported backend: {backend}")

        # 初始化 VAD
        self.vad = VADDetector() if enable_vad else None

        logger.info(
            f"LowLatencySTT initialized: backend={backend}, "
            f"vad_enabled={enable_vad}"
        )

    async def transcribe(
        self,
        audio_file: str,
        language: str = "zh"
    ) -> TranscriptionResult:
        """转写音频文件"""
        logger.info(f"Transcribing: {audio_file}")

        # VAD 预处理
        if self.vad:
            segments = self.vad.detect_speech_segments(audio_file)
            logger.info(f"VAD detected {len(segments)} speech segments")

        # 转写
        result = await self.engine.transcribe(audio_file, language)

        return result

    async def transcribe_stream(
        self,
        audio_file: str,
        language: str = "zh",
        callback: Optional[Callable[[TranscriptionResult], None]] = None
    ):
        """流式转写"""
        logger.info(f"Stream transcribing: {audio_file}")

        if hasattr(self.engine, 'transcribe_stream'):
            await self.engine.transcribe_stream(audio_file, language, callback)
        else:
            # 回退到普通转写
            result = await self.transcribe(audio_file, language)
            if callback:
                callback(result)

    def get_latency_stats(self) -> Dict[str, Any]:
        """获取延迟统计"""
        return {
            "backend": self.backend.value,
            "vad_enabled": self.enable_vad,
            "expected_latency_ms": self._estimate_latency()
        }

    def _estimate_latency(self) -> int:
        """估算延迟"""
        if self.backend == STTBackend.OPENAI:
            return 2000  # ~2s
        elif self.backend == STTBackend.FASTER_WHISPER:
            return 500   # ~0.5s
        else:
            return 1000  # ~1s


# ============================================================================
# 演示和测试
# ============================================================================

async def demo_vad_detection():
    """演示 VAD 检测"""
    print("\n" + "=" * 80)
    print("VAD Detection Demo")
    print("=" * 80)

    # 检查是否有测试音频
    test_audio = Path("tts_output/test_1_opening_friendly.mp3")

    if not test_audio.exists():
        print("\n[SKIP] No test audio file found")
        print("  Please run week7_day1_tts_emotion.py first to generate test audio")
        return

    print(f"\n[Test Audio] {test_audio}")

    try:
        VADDetector(
            sample_rate=16000,
            frame_duration_ms=30,
            aggressiveness=3
        )

        # 注意：MP3 需要先转换为 WAV
        print("\n[Note] VAD requires WAV format")
        print("  MP3 files need to be converted first")
        print("  Skipping VAD demo for now")

    except Exception as e:
        print(f"\n[ERROR] {e}")


async def demo_stt_transcription():
    """演示 STT 转写"""
    print("\n" + "=" * 80)
    print("STT Transcription Demo")
    print("=" * 80)

    # 检查是否有测试音频
    test_audio = Path("tts_output/test_1_opening_friendly.mp3")

    if not test_audio.exists():
        print("\n[SKIP] No test audio file found")
        print("  Please run week7_day1_tts_emotion.py first to generate test audio")
        return

    print(f"\n[Test Audio] {test_audio}")

    try:
        # 使用 Faster Whisper（本地，低延迟）
        stt = LowLatencySTT(
            backend=STTBackend.FASTER_WHISPER,
            enable_vad=False  # MP3 不支持 VAD
        )

        print("\n[Transcribing...]")
        result = await stt.transcribe(str(test_audio), language="zh")

        print("\n[Result]")
        print(f"  Text: {result.text}")
        print(f"  Type: {result.type.value}")
        print(f"  Duration: {result.duration:.2f}s")
        print(f"  Language: {result.language}")

        # 延迟统计
        stats = stt.get_latency_stats()
        print("\n[Latency Stats]")
        print(f"  Backend: {stats['backend']}")
        print(f"  VAD Enabled: {stats['vad_enabled']}")
        print(f"  Expected Latency: {stats['expected_latency_ms']}ms")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\n[Note] Faster Whisper requires installation:")
        print("  pip install faster-whisper")


async def demo_stream_transcription():
    """演示流式转写"""
    print("\n" + "=" * 80)
    print("Stream Transcription Demo")
    print("=" * 80)

    # 检查是否有测试音频
    test_audio = Path("tts_output/test_3_pitch_confident.mp3")

    if not test_audio.exists():
        print("\n[SKIP] No test audio file found")
        return

    print(f"\n[Test Audio] {test_audio}")

    try:
        stt = LowLatencySTT(
            backend=STTBackend.FASTER_WHISPER,
            enable_vad=False
        )

        print("\n[Streaming...]")

        # 回调函数
        def on_partial_result(result: TranscriptionResult):
            print(f"  [{result.type.value}] {result.text}")

        await stt.transcribe_stream(
            str(test_audio),
            language="zh",
            callback=on_partial_result
        )

        print("\n[Stream completed]")

    except Exception as e:
        print(f"\n[ERROR] {e}")


async def demo_latency_comparison():
    """演示延迟对比"""
    print("\n" + "=" * 80)
    print("Latency Comparison Demo")
    print("=" * 80)

    backends = [
        (STTBackend.FASTER_WHISPER, "Faster Whisper (Local)"),
        (STTBackend.OPENAI, "OpenAI Whisper (API)")
    ]

    for backend, name in backends:
        print(f"\n[{name}]")

        try:
            stt = LowLatencySTT(backend=backend, enable_vad=False)
            stats = stt.get_latency_stats()

            print(f"  Expected Latency: {stats['expected_latency_ms']}ms")
            print(f"  VAD Enabled: {stats['vad_enabled']}")

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
    print("Phase 3B Week 7 Day 3-4: STT with Low Latency")
    print("=" * 80)

    # 1. 演示 VAD 检测
    await demo_vad_detection()

    # 2. 演示 STT 转写
    await demo_stt_transcription()

    # 3. 演示流式转写
    await demo_stream_transcription()

    # 4. 演示延迟对比
    await demo_latency_comparison()

    print("\n" + "=" * 80)
    print("All demos completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
