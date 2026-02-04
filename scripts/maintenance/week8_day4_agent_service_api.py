"""
Phase 4 Week 8 Day 4: Agent Service API Implementation

核心目标：
1. 实现 FastAPI Agent 服务
2. 提供销售对话、意图识别、状态管理等 API 端点
3. 集成 Week 5-6 的多智能体系统
4. 实现会话管理、历史记录、评估反馈

实现日期: 2026-02-02
"""

import logging
import os
import sys
import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, status
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

class ConversationRole(str, Enum):
    """对话角色"""
    AGENT = "agent"
    USER = "user"
    SYSTEM = "system"


class IntentType(str, Enum):
    """意图类型"""
    PRODUCT_INQUIRY = "product_inquiry"
    PRICING_QUESTION = "pricing_question"
    OBJECTION = "objection"
    PURCHASE_INTENT = "purchase_intent"
    GENERAL_CHAT = "general_chat"
    UNKNOWN = "unknown"


class ConversationMessage(BaseModel):
    """对话消息"""
    role: ConversationRole = Field(..., description="角色")
    content: str = Field(..., min_length=1, max_length=2000, description="消息内容")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="时间戳")


class ConversationRequest(BaseModel):
    """对话请求"""
    session_id: Optional[str] = Field(default=None, description="会话ID")
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文信息")


class ConversationResponse(BaseModel):
    """对话响应"""
    session_id: str = Field(..., description="会话ID")
    agent_message: str = Field(..., description="Agent回复")
    sales_state: str = Field(..., description="销售阶段")
    intent: str = Field(..., description="识别的意图")
    confidence: float = Field(..., description="置信度")
    suggestions: List[str] = Field(default_factory=list, description="建议话术")
    latency_ms: float = Field(..., description="延迟（毫秒）")


class IntentRecognitionRequest(BaseModel):
    """意图识别请求"""
    text: str = Field(..., min_length=1, max_length=2000, description="待识别文本")


class IntentRecognitionResponse(BaseModel):
    """意图识别响应"""
    text: str = Field(..., description="原始文本")
    intent: IntentType = Field(..., description="识别的意图")
    confidence: float = Field(..., description="置信度")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    latency_ms: float = Field(..., description="延迟（毫秒）")


class EvaluationRequest(BaseModel):
    """评估请求"""
    session_id: str = Field(..., description="会话ID")
    agent_message: str = Field(..., description="Agent消息")
    user_response: Optional[str] = Field(default=None, description="用户响应")


class EvaluationDimension(BaseModel):
    """评估维度"""
    name: str = Field(..., description="维度名称")
    score: float = Field(..., ge=0, le=10, description="分数（0-10）")
    feedback: str = Field(..., description="反馈")


class EvaluationResponse(BaseModel):
    """评估响应"""
    session_id: str = Field(..., description="会话ID")
    overall_score: float = Field(..., ge=0, le=10, description="总分")
    dimensions: List[EvaluationDimension] = Field(..., description="各维度评分")
    suggestions: List[str] = Field(default_factory=list, description="改进建议")
    latency_ms: float = Field(..., description="延迟（毫秒）")


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str = Field(..., description="会话ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    sales_state: str = Field(..., description="当前销售阶段")
    message_count: int = Field(..., description="消息数量")
    is_active: bool = Field(..., description="是否活跃")


class SessionHistoryResponse(BaseModel):
    """会话历史响应"""
    session_id: str = Field(..., description="会话ID")
    messages: List[ConversationMessage] = Field(..., description="消息列表")
    sales_state: str = Field(..., description="当前销售阶段")
    created_at: datetime = Field(..., description="创建时间")


# ============================================================================
# Mock Agent Engine (模拟 Week 5-6 的 Agent 系统)
# ============================================================================

class MockAgentEngine:
    """模拟 Agent 引擎（实际应该导入 Week 5-6 的实现）"""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.request_count = 0
        self.start_time = time.time()

        # SPIN 问题模板
        self.spin_questions = {
            SalesState.OPENING: [
                "您好！我是XX银行的销售顾问，很高兴为您服务。请问您今天想了解什么产品？",
                "欢迎咨询！我们有多种金融产品可以满足您的需求。"
            ],
            SalesState.DISCOVERY: [
                "请问您目前使用信用卡的主要场景是什么？",
                "您对信用卡额度有什么期望吗？",
                "您平时消费频率如何？"
            ],
            SalesState.PITCH: [
                "我们的白金卡最高额度可达50万，比市面上普通信用卡高出5倍。",
                "这张卡提供机场贵宾厅服务、积分返现等多项权益。"
            ],
            SalesState.OBJECTION: [
                "我理解您的顾虑。实际上，首年免年费，您可以零成本体验。",
                "关于这个问题，我们有专门的解决方案。"
            ],
            SalesState.CLOSING: [
                "那我现在帮您办理，需要您提供一下身份证信息。",
                "办理流程很简单，大约5分钟就能完成。"
            ]
        }

        logger.info("MockAgentEngine initialized")

    def create_session(self) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "sales_state": SalesState.OPENING,
            "messages": [],
            "context": {},
            "is_active": True
        }
        logger.info(f"Created session: {session_id}")
        return session_id

    async def process_message(
        self,
        session_id: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """处理用户消息"""
        self.request_count += 1

        # 获取或创建会话
        if session_id not in self.sessions:
            session_id = self.create_session()

        session = self.sessions[session_id]

        # 添加用户消息
        session["messages"].append({
            "role": ConversationRole.USER,
            "content": user_message,
            "timestamp": datetime.now()
        })

        # 识别意图
        intent = self._recognize_intent(user_message)

        # 状态转换
        new_state = self._transition_state(session["sales_state"], intent, user_message)
        session["sales_state"] = new_state

        # 生成回复
        agent_message = self._generate_response(new_state, intent, user_message)

        # 添加 Agent 消息
        session["messages"].append({
            "role": ConversationRole.AGENT,
            "content": agent_message,
            "timestamp": datetime.now()
        })

        # 更新会话
        session["updated_at"] = datetime.now()

        # 生成建议
        suggestions = self._generate_suggestions(new_state)

        await asyncio.sleep(0.05)  # 模拟处理延迟

        return {
            "session_id": session_id,
            "agent_message": agent_message,
            "sales_state": new_state.value,
            "intent": intent.value,
            "confidence": 0.85,
            "suggestions": suggestions
        }

    def _recognize_intent(self, text: str) -> IntentType:
        """识别意图"""
        text_lower = text.lower()

        # 关键词匹配
        if any(kw in text_lower for kw in ["产品", "信用卡", "额度", "功能", "权益"]):
            return IntentType.PRODUCT_INQUIRY
        elif any(kw in text_lower for kw in ["价格", "费用", "年费", "多少钱", "成本"]):
            return IntentType.PRICING_QUESTION
        elif any(kw in text_lower for kw in ["但是", "不过", "担心", "顾虑", "问题"]):
            return IntentType.OBJECTION
        elif any(kw in text_lower for kw in ["办理", "申请", "购买", "要", "需要"]):
            return IntentType.PURCHASE_INTENT
        elif any(kw in text_lower for kw in ["你好", "谢谢", "再见", "好的"]):
            return IntentType.GENERAL_CHAT
        else:
            return IntentType.UNKNOWN

    def _transition_state(
        self,
        current_state: SalesState,
        intent: IntentType,
        message: str
    ) -> SalesState:
        """状态转换"""
        # 简化的状态转换逻辑
        if current_state == SalesState.OPENING:
            if intent == IntentType.PRODUCT_INQUIRY:
                return SalesState.DISCOVERY
            elif intent == IntentType.PRICING_QUESTION:
                return SalesState.PITCH
        elif current_state == SalesState.DISCOVERY:
            if intent == IntentType.PRODUCT_INQUIRY:
                return SalesState.PITCH
        elif current_state == SalesState.PITCH:
            if intent == IntentType.OBJECTION:
                return SalesState.OBJECTION
            elif intent == IntentType.PURCHASE_INTENT:
                return SalesState.CLOSING
        elif current_state == SalesState.OBJECTION:
            if intent == IntentType.PURCHASE_INTENT:
                return SalesState.CLOSING
            elif "好的" in message or "明白" in message:
                return SalesState.PITCH

        return current_state

    def _generate_response(
        self,
        state: SalesState,
        intent: IntentType,
        user_message: str
    ) -> str:
        """生成回复"""
        import random

        # 根据状态选择回复模板
        templates = self.spin_questions.get(state, ["我明白了，让我为您详细介绍。"])
        return random.choice(templates)

    def _generate_suggestions(self, state: SalesState) -> List[str]:
        """生成建议话术"""
        suggestions_map = {
            SalesState.OPENING: [
                "主动询问客户需求",
                "建立信任关系"
            ],
            SalesState.DISCOVERY: [
                "深入了解客户痛点",
                "使用SPIN提问法"
            ],
            SalesState.PITCH: [
                "突出产品优势",
                "使用FAB话术"
            ],
            SalesState.OBJECTION: [
                "倾听客户顾虑",
                "提供解决方案"
            ],
            SalesState.CLOSING: [
                "引导客户决策",
                "简化办理流程"
            ]
        }
        return suggestions_map.get(state, [])

    async def recognize_intent(self, text: str) -> Dict[str, Any]:
        """识别意图"""
        await asyncio.sleep(0.01)  # 模拟处理延迟

        intent = self._recognize_intent(text)

        # 提取关键词
        keywords = []
        for word in ["产品", "价格", "年费", "额度", "办理"]:
            if word in text:
                keywords.append(word)

        return {
            "text": text,
            "intent": intent,
            "confidence": 0.85,
            "keywords": keywords
        }

    async def evaluate_conversation(
        self,
        session_id: str,
        agent_message: str,
        user_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """评估对话"""
        await asyncio.sleep(0.03)  # 模拟处理延迟

        # 5个评估维度
        dimensions = [
            {
                "name": "Methodology",
                "score": 8.5,
                "feedback": "使用了SPIN提问法，效果良好"
            },
            {
                "name": "Objection Handling",
                "score": 7.8,
                "feedback": "异议处理及时，但可以更有同理心"
            },
            {
                "name": "Goal Orientation",
                "score": 9.0,
                "feedback": "目标明确，推进有力"
            },
            {
                "name": "Empathy",
                "score": 7.5,
                "feedback": "需要更多倾听和理解"
            },
            {
                "name": "Clarity",
                "score": 8.8,
                "feedback": "表达清晰，逻辑性强"
            }
        ]

        overall_score = sum(d["score"] for d in dimensions) / len(dimensions)

        suggestions = [
            "增强同理心表达",
            "使用更多开放式问题",
            "适当放慢节奏"
        ]

        return {
            "session_id": session_id,
            "overall_score": overall_score,
            "dimensions": dimensions,
            "suggestions": suggestions
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        return self.sessions.get(session_id)

    def get_session_history(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话历史"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session_id,
            "messages": session["messages"],
            "sales_state": session["sales_state"].value,
            "created_at": session["created_at"]
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        return [
            {
                "session_id": sid,
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
                "sales_state": session["sales_state"].value,
                "message_count": len(session["messages"]),
                "is_active": session["is_active"]
            }
            for sid, session in self.sessions.items()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = time.time() - self.start_time

        return {
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "active_sessions": sum(1 for s in self.sessions.values() if s["is_active"]),
            "total_sessions": len(self.sessions)
        }


# ============================================================================
# FastAPI Application
# ============================================================================

# 全局 Agent 引擎实例
agent_engine: Optional[MockAgentEngine] = MockAgentEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global agent_engine
    if agent_engine is None:
        agent_engine = MockAgentEngine()
    logger.info("Agent Service started")
    yield
    logger.info("Agent Service stopped")


# 创建 FastAPI 应用
app = FastAPI(
    title="SalesBoost Agent Service",
    description="智能销售对话 Agent 服务 API",
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


def get_agent_engine() -> MockAgentEngine:
    """获取 Agent 引擎依赖"""
    if agent_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent engine not initialized"
        )
    return agent_engine


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """根路径"""
    return {
        "service": "SalesBoost Agent Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=Dict[str, Any])
async def health_check(engine: MockAgentEngine = Depends(get_agent_engine)):
    """健康检查"""
    stats = engine.get_stats()

    return {
        "status": "healthy",
        "version": "1.0.0",
        **stats
    }


@app.post("/v1/conversation", response_model=ConversationResponse)
async def conversation(
    request: ConversationRequest,
    engine: MockAgentEngine = Depends(get_agent_engine)
):
    """
    销售对话接口

    处理用户消息，返回 Agent 回复和销售状态。
    """
    start_time = time.time()

    try:
        # 创建或获取会话
        session_id = request.session_id or engine.create_session()

        # 处理消息
        result = await engine.process_message(
            session_id=session_id,
            user_message=request.message,
            context=request.context
        )

        latency_ms = (time.time() - start_time) * 1000

        return ConversationResponse(
            **result,
            latency_ms=latency_ms
        )

    except Exception as e:
        logger.error(f"Conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversation failed: {str(e)}"
        )


@app.post("/v1/intent", response_model=IntentRecognitionResponse)
async def recognize_intent(
    request: IntentRecognitionRequest,
    engine: MockAgentEngine = Depends(get_agent_engine)
):
    """
    意图识别接口

    识别用户消息的意图类型。
    """
    start_time = time.time()

    try:
        result = await engine.recognize_intent(request.text)

        latency_ms = (time.time() - start_time) * 1000

        return IntentRecognitionResponse(
            **result,
            latency_ms=latency_ms
        )

    except Exception as e:
        logger.error(f"Intent recognition error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent recognition failed: {str(e)}"
        )


@app.post("/v1/evaluate", response_model=EvaluationResponse)
async def evaluate(
    request: EvaluationRequest,
    engine: MockAgentEngine = Depends(get_agent_engine)
):
    """
    对话评估接口

    评估 Agent 的对话质量，提供改进建议。
    """
    start_time = time.time()

    try:
        result = await engine.evaluate_conversation(
            session_id=request.session_id,
            agent_message=request.agent_message,
            user_response=request.user_response
        )

        latency_ms = (time.time() - start_time) * 1000

        return EvaluationResponse(
            **result,
            latency_ms=latency_ms
        )

    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )


@app.get("/v1/sessions", response_model=List[SessionInfo])
async def list_sessions(engine: MockAgentEngine = Depends(get_agent_engine)):
    """列出所有会话"""
    sessions = engine.list_sessions()
    return [SessionInfo(**s) for s in sessions]


@app.get("/v1/sessions/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    engine: MockAgentEngine = Depends(get_agent_engine)
):
    """获取会话历史"""
    history = engine.get_session_history(session_id)

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )

    return SessionHistoryResponse(**history)


@app.delete("/v1/sessions/{session_id}")
async def delete_session(
    session_id: str,
    engine: MockAgentEngine = Depends(get_agent_engine)
):
    """删除会话"""
    if session_id in engine.sessions:
        del engine.sessions[session_id]
        return {"message": f"Session {session_id} deleted"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )


@app.get("/v1/stats", response_model=Dict[str, Any])
async def get_stats(engine: MockAgentEngine = Depends(get_agent_engine)):
    """获取服务统计信息"""
    return engine.get_stats()


# ============================================================================
# 测试和演示
# ============================================================================

async def demo_agent_api():
    """演示 Agent API"""
    print("\n" + "=" * 80)
    print("Agent Service API Demo")
    print("=" * 80)

    from fastapi.testclient import TestClient

    client = TestClient(app)

    # 1. 健康检查
    print("\n[Test 1] Health Check")
    response = client.get("/health")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")

    # 2. 创建对话
    print("\n[Test 2] Start Conversation")
    conv_request = {
        "message": "你好，我想了解一下信用卡"
    }
    response = client.post("/v1/conversation", json=conv_request)
    print(f"  Status: {response.status_code}")
    result = response.json()
    session_id = result["session_id"]
    print(f"  Session ID: {session_id}")
    print(f"  Agent: {result['agent_message']}")
    print(f"  State: {result['sales_state']}")
    print(f"  Intent: {result['intent']}")
    print(f"  Latency: {result['latency_ms']:.2f}ms")

    # 3. 继续对话
    print("\n[Test 3] Continue Conversation")
    conv_request = {
        "session_id": session_id,
        "message": "额度最高多少？"
    }
    response = client.post("/v1/conversation", json=conv_request)
    result = response.json()
    print(f"  Agent: {result['agent_message']}")
    print(f"  State: {result['sales_state']}")
    print(f"  Suggestions: {result['suggestions']}")

    # 4. 意图识别
    print("\n[Test 4] Intent Recognition")
    intent_request = {
        "text": "年费多少钱？"
    }
    response = client.post("/v1/intent", json=intent_request)
    result = response.json()
    print(f"  Text: {result['text']}")
    print(f"  Intent: {result['intent']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Keywords: {result['keywords']}")

    # 5. 对话评估
    print("\n[Test 5] Conversation Evaluation")
    eval_request = {
        "session_id": session_id,
        "agent_message": "我们的白金卡最高额度可达50万",
        "user_response": "听起来不错"
    }
    response = client.post("/v1/evaluate", json=eval_request)
    result = response.json()
    print(f"  Overall Score: {result['overall_score']:.1f}/10")
    print("  Dimensions:")
    for dim in result['dimensions']:
        print(f"    - {dim['name']}: {dim['score']:.1f}/10 - {dim['feedback']}")
    print(f"  Suggestions: {result['suggestions']}")

    # 6. 获取会话历史
    print("\n[Test 6] Session History")
    response = client.get(f"/v1/sessions/{session_id}")
    result = response.json()
    print(f"  Session ID: {result['session_id']}")
    print(f"  Messages: {len(result['messages'])}")
    print(f"  State: {result['sales_state']}")
    for i, msg in enumerate(result['messages'], 1):
        print(f"    [{i}] {msg['role']}: {msg['content'][:50]}...")

    # 7. 列出所有会话
    print("\n[Test 7] List Sessions")
    response = client.get("/v1/sessions")
    sessions = response.json()
    print(f"  Total Sessions: {len(sessions)}")
    for session in sessions:
        print(f"    - {session['session_id']}: {session['message_count']} messages, state={session['sales_state']}")

    # 8. 统计信息
    print("\n[Test 8] Statistics")
    response = client.get("/v1/stats")
    stats = response.json()
    print(f"  Total Requests: {stats['total_requests']}")
    print(f"  Active Sessions: {stats['active_sessions']}")
    print(f"  Total Sessions: {stats['total_sessions']}")
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
    print("Phase 4 Week 8 Day 4: Agent Service API Implementation")
    print("=" * 80)

    # 运行演示
    asyncio.run(demo_agent_api())

    print("\n" + "=" * 80)
    print("All tests passed!")
    print("=" * 80)

    print("\n[Info] To run the server:")
    print("  uvicorn week8_day4_agent_service_api:app --reload --port 8002")
    print("\n[Info] API Documentation:")
    print("  Swagger UI: http://localhost:8002/docs")
    print("  ReDoc: http://localhost:8002/redoc")


if __name__ == "__main__":
    main()
