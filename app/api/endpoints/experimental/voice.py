"""
Voice Interface (E1)
定义 ASR (语音转文本) 和 TTS (文本转语音) 接口标准
当前实现为 Mock，未来可对接 OpenAI Whisper / TTS
"""
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "alloy"

class TTSResponse(BaseModel):
    audio_url: str # 或 base64
    duration_seconds: float

class ASRResponse(BaseModel):
    text: str
    confidence: float

@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(req: TTSRequest):
    """
    Mock TTS: 返回一个静态音频链接
    """
    logger.info(f"TTS Request: {req.text[:50]}...")
    # 模拟处理延迟
    # await asyncio.sleep(0.5)
    return TTSResponse(
        audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", # 示例音频
        duration_seconds=5.0
    )

@router.post("/asr", response_model=ASRResponse)
async def audio_to_speech(file: UploadFile = File(...)):
    """
    Mock ASR: 返回固定文本
    """
    logger.info(f"ASR Request: {file.filename}")
    return ASRResponse(
        text="这是一个模拟的语音转文本结果。实际上，这里应该调用 Whisper API。",
        confidence=0.98
    )
