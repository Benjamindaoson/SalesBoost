"""
Phase 4 Week 8 Day 5-6: Voice Service API with WebSocket Streaming

核心目标：
1. 实现 FastAPI Voice 服务
2. 提供 TTS、STT、语音对话等 API 端点
3. 实现 WebSocket 实时语音流传输
4. 集成 Week 7 的语音交互系统

实现日期: 2026-02-02
"""

import logging
import os
import sys
import asyncio
import time
import json
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.agents.conversation import SalesState

logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================

class VoiceEmotion(str, Enum):
    """语音情感"""
    FRIENDLY = "friendly"
    CURIOUS = "curious"
    CONFIDENT = "confident"
    EMPATHETIC = "empathetic"
    ENTHUSIASTIC = "enthusiastic"
    NEUTRAL = "neutral"


class TTSRequest(BaseModel):
    """TTS 请求"""
    text: str = Field(..., min_length=1, max_length=2000, description="待合成文本")
    emotion: Optional[VoiceEmotion] = Field(default=VoiceEmotion.NEUTRAL, description="语音情感")
    sales_state: Optional[str] = Field(default=None, description="销售阶段")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="语速")
    pitch: float = Field(default=1.0, ge=0.5, le=2.0, description="音调")


class TTSResponse(BaseModel):
    """TTS 响应"""
    audio_base64: str = Field(..., description="Base64编码的音频数据")
    emotion: str = Field(..., description="使用的情感")
    duration_ms: float = Field(..., description="音频时长（毫秒）")
    latency_ms: float = Field(..., description="合成延迟（毫秒）")


class STTRequest(BaseModel):
    """STT 请求"""
    audio_base64: str = Field(..., description="Base64编码的音频数据")
    language: str = Field(default="zh", description="语言代码")


class STTResponse(BaseModel):
    """STT 响应"""
    text: str = Field(..., description="识别的文本")
    confidence: float = Field(..., description="置信度")
    language: str = Field(..., description="语言")
    latency_ms: float = Field(..., description="识别延迟（毫秒）")


class VoiceConversationRequest(BaseModel):
    """语音对话请求"""
    session_id: Optional[str] = Field(default=None, description="会话ID")
    audio_base64: str = Field(..., description="Base64编码的用户语音")
    language: str = Field(default="zh", description="语言代码")


class VoiceConversationResponse(BaseModel):
    """语音对话响应"""
    session_id: str = Field(..., description="会话ID")
    user_text: str = Field(..., description="用户说的话")
    agent_text: str = Field(..., description="Agent回复文本")
    agent_audio_base64: str = Field(..., description="Agent回复语音")
    sales_state: str = Field(..., description="销售阶段")
    emotion: str = Field(..., description="使用的情感")
    latency_ms: float = Field(..., description="总延迟（毫秒）")


class WebSocketMessage(BaseModel):
    """WebSocket 消息"""
    type: str = Field(..., description="消息类型")
    data: Dict[str, Any] = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


# ============================================================================
# Mock Voice Engine (模拟 Week 7 的语音系统)
# ============================================================================

class MockVoiceEngine:
    """模拟语音引擎（实际应该导入 Week 7 的实现）"""

    def __init__(self):
        self.request_count = 0
        self.start_time = time.time()
        self.active_connections: Dict[str, WebSocket] = {}

        # 情感映射
        self.emotion_mapping = {
            SalesState.OPENING: VoiceEmotion.FRIENDLY,
            SalesState.DISCOVERY: VoiceEmotion.CURIOUS,
            SalesState.PITCH: VoiceEmotion.CONFIDENT,
            SalesState.OBJECTION: VoiceEmotion.EMPATHETIC,
            SalesState.CLOSING: VoiceEmotion.ENTHUSIASTIC,
            SalesState.COMPLETED: VoiceEmotion.FRIENDLY,
            SalesState.FAILED: VoiceEmotion.NEUTRAL
        }

        logger.info("MockVoiceEngine initialized")

    async def synthesize_speech(
        self,
        text: str,
        emotion: VoiceEmotion = VoiceEmotion.NEUTRAL,
        sales_state: Optional[SalesState] = None,
        speed: float = 1.0,
        pitch: float = 1.0
    ) -> bytes:
        """合成语音"""
        self.request_count += 1

        # 如果指定了销售阶段，使用对应的情感
        if sales_state:
            emotion = self.emotion_mapping.get(sales_state, VoiceEmotion.NEUTRAL)

        # 模拟 TTS 延迟
        await asyncio.sleep(0.05)

        # 生成模拟音频数据（实际应该调用 Week 7 的 EmotionalTTS）
        audio_data = f"[AUDIO: {text[:50]}... | emotion={emotion.value}]".encode()

        logger.info(f"Synthesized speech: {len(audio_data)} bytes, emotion={emotion.value}")
        return audio_data

    async def recognize_speech(
        self,
        audio_data: bytes,
        language: str = "zh"
    ) -> Dict[str, Any]:
        """识别语音"""
        self.request_count += 1

        # 模拟 STT 延迟
        await asyncio.sleep(0.03)

        # 模拟识别结果（实际应该调用 Week 7 的 LowLatencySTT）
        text = f"[Recognized from {len(audio_data)} bytes audio]"
        confidence = 0.92

        logger.info(f"Recognized speech: {text}, confidence={confidence}")
        return {
            "text": text,
            "confidence": confidence,
            "language": language
        }

    async def process_voice_conversation(
        self,
        session_id: str,
        audio_data: bytes,
        language: str = "zh"
    ) -> Dict[str, Any]:
        """处理语音对话"""
        # 1. STT: 识别用户语音
        stt_result = await self.recognize_speech(audio_data, language)
        user_text = stt_result["text"]

        # 2. Agent: 生成回复（模拟调用 Agent Service）
        agent_text = f"我理解您说的是：{user_text}。让我为您详细介绍。"
        sales_state = SalesState.DISCOVERY

        # 3. TTS: 合成 Agent 语音
        agent_audio = await self.synthesize_speech(
            agent_text,
            sales_state=sales_state
        )

        emotion = self.emotion_mapping.get(sales_state, VoiceEmotion.NEUTRAL)

        return {
            "session_id": session_id,
            "user_text": user_text,
            "agent_text": agent_text,
            "agent_audio": agent_audio,
            "sales_state": sales_state.value,
            "emotion": emotion.value
        }

    async def stream_audio(self, text: str, emotion: VoiceEmotion) -> bytes:
        """流式生成音频（用于 WebSocket）"""
        # 模拟分块生成音频
        chunk_size = 1024
        total_size = len(text) * 100  # 模拟音频大小

        for i in range(0, total_size, chunk_size):
            chunk = f"[AUDIO_CHUNK_{i}]".encode()
            await asyncio.sleep(0.01)  # 模拟生成延迟
            yield chunk

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = time.time() - self.start_time

        return {
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "active_connections": len(self.active_connections)
        }


# ============================================================================
# FastAPI Application
# ============================================================================

# 全局语音引擎实例
voice_engine: Optional[MockVoiceEngine] = MockVoiceEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global voice_engine
    if voice_engine is None:
        voice_engine = MockVoiceEngine()
    logger.info("Voice Service started")
    yield
    logger.info("Voice Service stopped")


# 创建 FastAPI 应用
app = FastAPI(
    title="SalesBoost Voice Service",
    description="智能语音交互服务 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_voice_engine() -> MockVoiceEngine:
    """获取语音引擎依赖"""
    if voice_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice engine not initialized"
        )
    return voice_engine


# ============================================================================
# REST API Endpoints
# ============================================================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """根路径"""
    return {
        "service": "SalesBoost Voice Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=Dict[str, Any])
async def health_check(engine: MockVoiceEngine = Depends(get_voice_engine)):
    """健康检查"""
    stats = engine.get_stats()

    return {
        "status": "healthy",
        "version": "1.0.0",
        **stats
    }


@app.post("/v1/tts", response_model=TTSResponse)
async def text_to_speech(
    request: TTSRequest,
    engine: MockVoiceEngine = Depends(get_voice_engine)
):
    """
    文本转语音 (TTS)

    将文本转换为语音，支持情感控制。
    """
    start_time = time.time()

    try:
        # 解析销售阶段
        sales_state = None
        if request.sales_state:
            try:
                sales_state = SalesState(request.sales_state)
            except ValueError:
                pass

        # 合成语音
        audio_data = await engine.synthesize_speech(
            text=request.text,
            emotion=request.emotion,
            sales_state=sales_state,
            speed=request.speed,
            pitch=request.pitch
        )

        # Base64 编码
        audio_base64 = base64.b64encode(audio_data).decode()

        latency_ms = (time.time() - start_time) * 1000

        # 估算音频时长（简化）
        duration_ms = len(request.text) * 100  # 假设每字100ms

        return TTSResponse(
            audio_base64=audio_base64,
            emotion=request.emotion.value,
            duration_ms=duration_ms,
            latency_ms=latency_ms
        )

    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS failed: {str(e)}"
        )


@app.post("/v1/stt", response_model=STTResponse)
async def speech_to_text(
    request: STTRequest,
    engine: MockVoiceEngine = Depends(get_voice_engine)
):
    """
    语音转文本 (STT)

    将语音转换为文本。
    """
    start_time = time.time()

    try:
        # Base64 解码
        audio_data = base64.b64decode(request.audio_base64)

        # 识别语音
        result = await engine.recognize_speech(audio_data, request.language)

        latency_ms = (time.time() - start_time) * 1000

        return STTResponse(
            text=result["text"],
            confidence=result["confidence"],
            language=result["language"],
            latency_ms=latency_ms
        )

    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"STT failed: {str(e)}"
        )


@app.post("/v1/voice-conversation", response_model=VoiceConversationResponse)
async def voice_conversation(
    request: VoiceConversationRequest,
    engine: MockVoiceEngine = Depends(get_voice_engine)
):
    """
    语音对话

    端到端的语音对话：STT -> Agent -> TTS
    """
    start_time = time.time()

    try:
        # Base64 解码
        audio_data = base64.b64decode(request.audio_base64)

        # 生成或使用会话ID
        import uuid
        session_id = request.session_id or str(uuid.uuid4())

        # 处理语音对话
        result = await engine.process_voice_conversation(
            session_id=session_id,
            audio_data=audio_data,
            language=request.language
        )

        # Base64 编码 Agent 语音
        agent_audio_base64 = base64.b64encode(result["agent_audio"]).decode()

        latency_ms = (time.time() - start_time) * 1000

        return VoiceConversationResponse(
            session_id=result["session_id"],
            user_text=result["user_text"],
            agent_text=result["agent_text"],
            agent_audio_base64=agent_audio_base64,
            sales_state=result["sales_state"],
            emotion=result["emotion"],
            latency_ms=latency_ms
        )

    except Exception as e:
        logger.error(f"Voice conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice conversation failed: {str(e)}"
        )


@app.get("/v1/stats", response_model=Dict[str, Any])
async def get_stats(engine: MockVoiceEngine = Depends(get_voice_engine)):
    """获取服务统计信息"""
    return engine.get_stats()


# ============================================================================
# WebSocket Endpoints
# ============================================================================

@app.websocket("/ws/voice-stream")
async def voice_stream_websocket(
    websocket: WebSocket,
    engine: MockVoiceEngine = Depends(get_voice_engine)
):
    """
    WebSocket 语音流传输

    实时双向语音流传输，支持：
    - 客户端发送音频流
    - 服务端实时识别并回复
    - 流式 TTS 输出
    """
    await websocket.accept()
    connection_id = str(id(websocket))
    engine.active_connections[connection_id] = websocket

    logger.info(f"WebSocket connected: {connection_id}")

    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "data": {
                "connection_id": connection_id,
                "message": "Voice stream connected"
            },
            "timestamp": datetime.now().isoformat()
        })

        while True:
            # 接收客户端消息
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "audio_chunk":
                # 处理音频块
                audio_base64 = message.get("data", {}).get("audio_base64")

                if audio_base64:
                    # 解码音频
                    audio_data = base64.b64decode(audio_base64)

                    # 识别语音
                    stt_result = await engine.recognize_speech(audio_data)

                    # 发送识别结果
                    await websocket.send_json({
                        "type": "transcription",
                        "data": {
                            "text": stt_result["text"],
                            "confidence": stt_result["confidence"]
                        },
                        "timestamp": datetime.now().isoformat()
                    })

                    # 生成回复
                    agent_text = f"收到：{stt_result['text']}"

                    # 流式发送 TTS 音频
                    await websocket.send_json({
                        "type": "agent_response",
                        "data": {
                            "text": agent_text,
                            "emotion": "friendly"
                        },
                        "timestamp": datetime.now().isoformat()
                    })

                    # 流式发送音频块
                    async for audio_chunk in engine.stream_audio(agent_text, VoiceEmotion.FRIENDLY):
                        chunk_base64 = base64.b64encode(audio_chunk).decode()
                        await websocket.send_json({
                            "type": "audio_chunk",
                            "data": {
                                "audio_base64": chunk_base64,
                                "is_final": False
                            },
                            "timestamp": datetime.now().isoformat()
                        })

                    # 发送结束标记
                    await websocket.send_json({
                        "type": "audio_chunk",
                        "data": {
                            "audio_base64": "",
                            "is_final": True
                        },
                        "timestamp": datetime.now().isoformat()
                    })

            elif msg_type == "ping":
                # 心跳响应
                await websocket.send_json({
                    "type": "pong",
                    "data": {},
                    "timestamp": datetime.now().isoformat()
                })

            elif msg_type == "close":
                # 客户端请求关闭
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # 清理连接
        if connection_id in engine.active_connections:
            del engine.active_connections[connection_id]
        logger.info(f"WebSocket cleaned up: {connection_id}")


# ============================================================================
# 测试和演示
# ============================================================================

async def demo_voice_api():
    """演示 Voice API"""
    print("\n" + "=" * 80)
    print("Voice Service API Demo")
    print("=" * 80)

    from fastapi.testclient import TestClient

    client = TestClient(app)

    # 1. 健康检查
    print("\n[Test 1] Health Check")
    response = client.get("/health")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")

    # 2. TTS 测试
    print("\n[Test 2] Text-to-Speech")
    tts_request = {
        "text": "您好！我是XX银行的销售顾问，很高兴为您服务。",
        "emotion": "friendly",
        "speed": 1.0,
        "pitch": 1.0
    }
    response = client.post("/v1/tts", json=tts_request)
    print(f"  Status: {response.status_code}")
    result = response.json()
    print(f"  Emotion: {result['emotion']}")
    print(f"  Duration: {result['duration_ms']:.2f}ms")
    print(f"  Latency: {result['latency_ms']:.2f}ms")
    print(f"  Audio (base64): {result['audio_base64'][:50]}...")

    # 3. STT 测试
    print("\n[Test 3] Speech-to-Text")
    # 模拟音频数据
    mock_audio = b"[Mock audio data for testing]"
    audio_base64 = base64.b64encode(mock_audio).decode()

    stt_request = {
        "audio_base64": audio_base64,
        "language": "zh"
    }
    response = client.post("/v1/stt", json=stt_request)
    print(f"  Status: {response.status_code}")
    result = response.json()
    print(f"  Text: {result['text']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Latency: {result['latency_ms']:.2f}ms")

    # 4. 语音对话测试
    print("\n[Test 4] Voice Conversation")
    voice_conv_request = {
        "audio_base64": audio_base64,
        "language": "zh"
    }
    response = client.post("/v1/voice-conversation", json=voice_conv_request)
    print(f"  Status: {response.status_code}")
    result = response.json()
    print(f"  Session ID: {result['session_id']}")
    print(f"  User: {result['user_text']}")
    print(f"  Agent: {result['agent_text']}")
    print(f"  State: {result['sales_state']}")
    print(f"  Emotion: {result['emotion']}")
    print(f"  Latency: {result['latency_ms']:.2f}ms")

    # 5. 不同情感测试
    print("\n[Test 5] Different Emotions")
    emotions = ["friendly", "confident", "empathetic", "enthusiastic"]
    for emotion in emotions:
        tts_request = {
            "text": f"这是{emotion}情感的测试",
            "emotion": emotion
        }
        response = client.post("/v1/tts", json=tts_request)
        result = response.json()
        print(f"  {emotion}: {result['latency_ms']:.2f}ms")

    # 6. 销售阶段情感映射测试
    print("\n[Test 6] Sales State Emotion Mapping")
    states = ["opening", "discovery", "pitch", "objection", "closing"]
    for state in states:
        tts_request = {
            "text": f"这是{state}阶段的话术",
            "sales_state": state
        }
        response = client.post("/v1/tts", json=tts_request)
        result = response.json()
        print(f"  {state} -> {result['emotion']}: {result['latency_ms']:.2f}ms")

    # 7. 统计信息
    print("\n[Test 7] Statistics")
    response = client.get("/v1/stats")
    stats = response.json()
    print(f"  Total Requests: {stats['total_requests']}")
    print(f"  Active Connections: {stats['active_connections']}")
    print(f"  Uptime: {stats['uptime_seconds']:.2f}s")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 80)
    print("Phase 4 Week 8 Day 5-6: Voice Service API with WebSocket Streaming")
    print("=" * 80)

    # 运行演示
    asyncio.run(demo_voice_api())

    print("\n" + "=" * 80)
    print("All tests passed!")
    print("=" * 80)

    print("\n[Info] To run the server:")
    print("  uvicorn week8_day5_voice_service_api:app --reload --port 8003")
    print("\n[Info] API Documentation:")
    print("  Swagger UI: http://localhost:8003/docs")
    print("  ReDoc: http://localhost:8003/redoc")
    print("\n[Info] WebSocket Endpoint:")
    print("  ws://localhost:8003/ws/voice-stream")


if __name__ == "__main__":
    main()
