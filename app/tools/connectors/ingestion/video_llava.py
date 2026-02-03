"""
Video-LLaVA 视频理解处理器

Video-LLaVA 是一个强大的视频理解模型，支持：
1. 视频内容理解
2. 关键帧提取
3. 场景描述
4. 动作识别
5. 字幕生成
"""
from __future__ import annotations

import base64
import io
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class VideoLLaVAClient:
    """
    Video-LLaVA 客户端

    支持视频理解和分析
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        api_key: Optional[str] = None,
        timeout: int = 300,  # 视频处理需要更长时间
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

    async def analyze_video(
        self,
        video_bytes: bytes,
        prompt: str = "Describe this video in detail.",
        max_frames: int = 8,
    ) -> str:
        """
        分析视频

        Args:
            video_bytes: 视频字节
            prompt: 提示词
            max_frames: 最大帧数

        Returns:
            视频描述
        """
        try:
            # 保存临时文件
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(video_bytes)
                temp_path = f.name

            # 提取关键帧
            frames = await self._extract_keyframes(temp_path, max_frames)

            # 编码帧为 base64
            frames_base64 = [base64.b64encode(frame).decode("utf-8") for frame in frames]

            # 构建请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                payload = {
                    "model": "video-llava",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                *[
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/jpeg;base64,{frame}"},
                                    }
                                    for frame in frames_base64
                                ],
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                    "max_tokens": 1000,
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
                        f"Video-LLaVA API error: {response.status_code} - {response.text}"
                    )
                    raise RuntimeError(f"API error: {response.status_code}")

        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            raise
        finally:
            # 清理临时文件
            try:
                Path(temp_path).unlink()
            except:
                pass

    async def _extract_keyframes(
        self, video_path: str, max_frames: int = 8
    ) -> List[bytes]:
        """
        提取关键帧

        Args:
            video_path: 视频路径
            max_frames: 最大帧数

        Returns:
            帧字节列表
        """
        try:
            import cv2

            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # 均匀采样
            frame_indices = [
                int(i * total_frames / max_frames) for i in range(max_frames)
            ]

            frames = []

            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()

                if ret:
                    # 转换为 JPEG
                    _, buffer = cv2.imencode(".jpg", frame)
                    frames.append(buffer.tobytes())

            cap.release()

            return frames

        except Exception as e:
            logger.error(f"Keyframe extraction failed: {e}")
            return []

    async def generate_summary(self, video_bytes: bytes) -> str:
        """
        生成视频摘要

        Args:
            video_bytes: 视频字节

        Returns:
            视频摘要
        """
        prompt = "Provide a concise summary of this video, including key scenes, actions, and any text or speech."

        return await self.analyze_video(video_bytes, prompt=prompt)

    async def extract_transcript(self, video_bytes: bytes) -> str:
        """
        提取视频字幕/转录

        Args:
            video_bytes: 视频字节

        Returns:
            转录文本
        """
        # 先提取音频
        audio_bytes = await self._extract_audio(video_bytes)

        # 使用 Whisper 转录
        from app.tools.connectors.ingestion.processors import WhisperProcessor

        whisper = WhisperProcessor()
        transcript = await whisper.process(audio_bytes, {})

        return transcript

    async def _extract_audio(self, video_bytes: bytes) -> bytes:
        """
        从视频提取音频

        Args:
            video_bytes: 视频字节

        Returns:
            音频字节
        """
        try:
            import subprocess

            # 保存临时视频
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(video_bytes)
                video_path = f.name

            # 提取音频
            audio_path = video_path.replace(".mp4", ".mp3")

            subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    video_path,
                    "-vn",
                    "-acodec",
                    "libmp3lame",
                    "-y",
                    audio_path,
                ],
                check=True,
                capture_output=True,
            )

            # 读取音频
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            # 清理
            Path(video_path).unlink()
            Path(audio_path).unlink()

            return audio_bytes

        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            return b""


class VideoLLaVAProcessor:
    """
    Video-LLaVA 处理器（用于 streaming pipeline）
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        api_key: Optional[str] = None,
    ):
        self.client = VideoLLaVAClient(base_url=base_url, api_key=api_key)

    async def process(self, content: bytes, metadata: Dict[str, Any]) -> str:
        """
        处理视频

        Args:
            content: 视频内容
            metadata: 元数据

        Returns:
            视频分析结果（Markdown 格式）
        """
        try:
            # 生成摘要
            summary = await self.client.generate_summary(content)

            # 提取转录（如果有音频）
            try:
                transcript = await self.client.extract_transcript(content)
            except:
                transcript = ""

            # 组合结果
            markdown = f"""# Video Analysis

## Summary
{summary}

## Transcript
{transcript if transcript else "No audio detected"}
"""

            return markdown

        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            return f"# Video Processing Failed\n\nError: {str(e)}"


# 部署脚本
DEPLOYMENT_SCRIPT = """
#!/bin/bash

# Video-LLaVA 部署脚本

# 克隆仓库
git clone https://github.com/PKU-YuanGroup/Video-LLaVA.git
cd Video-LLaVA

# 安装依赖
pip install -r requirements.txt

# 下载模型
huggingface-cli download LanguageBind/Video-LLaVA-7B

# 启动服务
python -m videollava.serve.api_server \\
    --model-path LanguageBind/Video-LLaVA-7B \\
    --host 0.0.0.0 \\
    --port 8002
"""


# 使用示例
USAGE_EXAMPLE = """
# 使用示例

from app.tools.connectors.ingestion.video_llava import VideoLLaVAClient

# 初始化客户端
client = VideoLLaVAClient(
    base_url="http://localhost:8002",
)

# 分析视频
with open("product_demo.mp4", "rb") as f:
    video_bytes = f.read()

# 生成摘要
summary = await client.generate_summary(video_bytes)
print(summary)

# 提取转录
transcript = await client.extract_transcript(video_bytes)
print(transcript)

# 自定义分析
analysis = await client.analyze_video(
    video_bytes,
    prompt="Identify all products shown in this video and describe their features.",
)
print(analysis)
"""
