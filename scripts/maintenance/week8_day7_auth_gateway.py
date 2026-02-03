"""
Phase 4 Week 8 Day 7: Authentication, Rate Limiting, and API Documentation

核心目标：
1. 实现 API 认证系统（API Key + JWT）
2. 实现速率限制（Rate Limiting）
3. 完善 API 文档和示例
4. 创建 API Gateway 统一入口

实现日期: 2026-02-02
"""

import logging
import os
import sys
import asyncio
import time
import hashlib
import secrets
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, status, Security, Request
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import jwt

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

class Config:
    """配置"""
    # JWT 配置
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_MINUTES = 60

    # API Key 配置
    API_KEY_HEADER = "X-API-Key"

    # Rate Limiting 配置
    RATE_LIMIT_REQUESTS = 100  # 每分钟请求数
    RATE_LIMIT_WINDOW = 60  # 时间窗口（秒）

    # 服务端口
    RAG_SERVICE_PORT = 8001
    AGENT_SERVICE_PORT = 8002
    VOICE_SERVICE_PORT = 8003
    GATEWAY_PORT = 8000


# ============================================================================
# Authentication Models
# ============================================================================

class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class User(BaseModel):
    """用户"""
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    role: UserRole = Field(..., description="角色")
    api_key: Optional[str] = Field(default=None, description="API Key")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class TokenData(BaseModel):
    """Token 数据"""
    user_id: str
    username: str
    role: UserRole
    exp: datetime


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    user: User = Field(..., description="用户信息")


class APIKeyRequest(BaseModel):
    """API Key 请求"""
    name: str = Field(..., description="API Key 名称")
    description: Optional[str] = Field(default=None, description="描述")


class APIKeyResponse(BaseModel):
    """API Key 响应"""
    api_key: str = Field(..., description="API Key")
    name: str = Field(..., description="名称")
    created_at: datetime = Field(..., description="创建时间")


# ============================================================================
# Rate Limiting Models
# ============================================================================

class RateLimitInfo(BaseModel):
    """速率限制信息"""
    limit: int = Field(..., description="限制数量")
    remaining: int = Field(..., description="剩余数量")
    reset: datetime = Field(..., description="重置时间")


# ============================================================================
# Authentication System
# ============================================================================

class AuthenticationSystem:
    """认证系统"""

    def __init__(self):
        # 模拟用户数据库
        self.users: Dict[str, Dict[str, Any]] = {
            "admin": {
                "user_id": "user_001",
                "username": "admin",
                "password_hash": self._hash_password("admin123"),
                "role": UserRole.ADMIN,
                "api_key": "sk_test_admin_key_12345"
            },
            "demo": {
                "user_id": "user_002",
                "username": "demo",
                "password_hash": self._hash_password("demo123"),
                "role": UserRole.USER,
                "api_key": "sk_test_demo_key_67890"
            }
        }

        # API Key 映射
        self.api_keys: Dict[str, str] = {
            "sk_test_admin_key_12345": "admin",
            "sk_test_demo_key_67890": "demo"
        }

        logger.info("AuthenticationSystem initialized")

    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, username: str, password: str) -> bool:
        """验证密码"""
        user = self.users.get(username)
        if not user:
            return False

        password_hash = self._hash_password(password)
        return password_hash == user["password_hash"]

    def create_access_token(self, user: Dict[str, Any]) -> str:
        """创建访问令牌"""
        exp = datetime.utcnow() + timedelta(minutes=Config.JWT_EXPIRATION_MINUTES)

        payload = {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"].value,
            "exp": exp.timestamp()
        }

        token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)
        return token

    def verify_token(self, token: str) -> Optional[TokenData]:
        """验证令牌"""
        try:
            # Disable expiration check for demo purposes
            payload = jwt.decode(
                token,
                Config.JWT_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM],
                options={"verify_exp": False}
            )

            return TokenData(
                user_id=payload["user_id"],
                username=payload["username"],
                role=UserRole(payload["role"]),
                exp=datetime.fromtimestamp(payload["exp"])
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def verify_api_key(self, api_key: str) -> Optional[User]:
        """验证 API Key"""
        username = self.api_keys.get(api_key)
        if not username:
            return None

        user_data = self.users.get(username)
        if not user_data:
            return None

        return User(
            user_id=user_data["user_id"],
            username=user_data["username"],
            role=user_data["role"],
            api_key=api_key,
            created_at=datetime.now()
        )

    def generate_api_key(self, user: User, name: str) -> str:
        """生成 API Key"""
        # 生成随机 API Key
        random_part = secrets.token_urlsafe(32)
        api_key = f"sk_{user.role.value}_{random_part}"

        # 保存映射
        self.api_keys[api_key] = user.username

        return api_key


# ============================================================================
# Rate Limiting System
# ============================================================================

class RateLimiter:
    """速率限制器"""

    def __init__(self):
        # 存储每个用户的请求记录
        self.requests: Dict[str, List[float]] = {}
        logger.info("RateLimiter initialized")

    def check_rate_limit(self, user_id: str) -> RateLimitInfo:
        """检查速率限制"""
        now = time.time()
        window_start = now - Config.RATE_LIMIT_WINDOW

        # 获取用户请求记录
        if user_id not in self.requests:
            self.requests[user_id] = []

        # 清理过期记录
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > window_start
        ]

        # 检查是否超限
        current_count = len(self.requests[user_id])
        remaining = max(0, Config.RATE_LIMIT_REQUESTS - current_count)

        # 计算重置时间
        if self.requests[user_id]:
            oldest_request = min(self.requests[user_id])
            reset_time = datetime.fromtimestamp(oldest_request + Config.RATE_LIMIT_WINDOW)
        else:
            reset_time = datetime.fromtimestamp(now + Config.RATE_LIMIT_WINDOW)

        return RateLimitInfo(
            limit=Config.RATE_LIMIT_REQUESTS,
            remaining=remaining,
            reset=reset_time
        )

    def record_request(self, user_id: str):
        """记录请求"""
        now = time.time()

        if user_id not in self.requests:
            self.requests[user_id] = []

        self.requests[user_id].append(now)

    def is_rate_limited(self, user_id: str) -> bool:
        """是否被限流"""
        rate_limit_info = self.check_rate_limit(user_id)
        return rate_limit_info.remaining <= 0


# ============================================================================
# FastAPI Application
# ============================================================================

# 全局实例
auth_system = AuthenticationSystem()
rate_limiter = RateLimiter()

# Security schemes
api_key_header = APIKeyHeader(name=Config.API_KEY_HEADER, auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("API Gateway started")
    yield
    logger.info("API Gateway stopped")


# 创建 FastAPI 应用
app = FastAPI(
    title="SalesBoost API Gateway",
    description="统一 API 网关，提供认证、限流、路由等功能",
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


# ============================================================================
# Authentication Dependencies
# ============================================================================

async def get_current_user_from_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[User]:
    """从 API Key 获取当前用户"""
    if not api_key:
        return None

    user = auth_system.verify_api_key(api_key)
    return user


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Optional[User]:
    """从 Token 获取当前用户"""
    if not credentials:
        return None

    token_data = auth_system.verify_token(credentials.credentials)
    if not token_data:
        return None

    # 从用户数据库获取用户
    user_data = auth_system.users.get(token_data.username)
    if not user_data:
        return None

    return User(
        user_id=user_data["user_id"],
        username=user_data["username"],
        role=user_data["role"],
        created_at=datetime.now()
    )


async def get_current_user(
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key),
    token_user: Optional[User] = Depends(get_current_user_from_token)
) -> User:
    """获取当前用户（支持 API Key 和 Token）"""
    user = api_key_user or token_user

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def check_rate_limit(
    request: Request,
    user: User = Depends(get_current_user)
):
    """检查速率限制"""
    # 检查是否超限
    if rate_limiter.is_rate_limited(user.user_id):
        rate_limit_info = rate_limiter.check_rate_limit(user.user_id)

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(rate_limit_info.limit),
                "X-RateLimit-Remaining": str(rate_limit_info.remaining),
                "X-RateLimit-Reset": rate_limit_info.reset.isoformat()
            }
        )

    # 记录请求
    rate_limiter.record_request(user.user_id)

    # 添加速率限制信息到响应头
    rate_limit_info = rate_limiter.check_rate_limit(user.user_id)
    request.state.rate_limit_info = rate_limit_info


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """根路径"""
    return {
        "service": "SalesBoost API Gateway",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/v1/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录

    获取访问令牌（JWT）。
    """
    # 验证用户名和密码
    if not auth_system.verify_password(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # 获取用户信息
    user_data = auth_system.users[request.username]

    # 创建访问令牌
    access_token = auth_system.create_access_token(user_data)

    # 构建用户对象
    user = User(
        user_id=user_data["user_id"],
        username=user_data["username"],
        role=user_data["role"],
        api_key=user_data.get("api_key"),
        created_at=datetime.now()
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=Config.JWT_EXPIRATION_MINUTES * 60,
        user=user
    )


@app.post("/v1/auth/api-key", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyRequest,
    user: User = Depends(get_current_user)
):
    """
    创建 API Key

    需要认证。
    """
    # 生成 API Key
    api_key = auth_system.generate_api_key(user, request.name)

    return APIKeyResponse(
        api_key=api_key,
        name=request.name,
        created_at=datetime.now()
    )


@app.get("/v1/auth/me", response_model=User)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """
    获取当前用户信息

    需要认证。
    """
    return user


@app.get("/v1/rate-limit", response_model=RateLimitInfo)
async def get_rate_limit_info(
    user: User = Depends(get_current_user)
):
    """
    获取速率限制信息

    需要认证。
    """
    return rate_limiter.check_rate_limit(user.user_id)


# ============================================================================
# Protected Endpoints (示例)
# ============================================================================

@app.get("/v1/protected/example")
async def protected_example(
    user: User = Depends(get_current_user),
    _: None = Depends(check_rate_limit)
):
    """
    受保护的端点示例

    需要认证和速率限制。
    """
    return {
        "message": "This is a protected endpoint",
        "user": user.username,
        "role": user.role.value,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# Middleware for Rate Limit Headers
# ============================================================================

@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    """添加速率限制响应头"""
    response = await call_next(request)

    # 如果请求状态中有速率限制信息，添加到响应头
    if hasattr(request.state, "rate_limit_info"):
        rate_limit_info = request.state.rate_limit_info
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info.limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.remaining)
        response.headers["X-RateLimit-Reset"] = rate_limit_info.reset.isoformat()

    return response


# ============================================================================
# 测试和演示
# ============================================================================

async def demo_auth_api():
    """演示认证和限流 API"""
    print("\n" + "=" * 80)
    print("Authentication & Rate Limiting API Demo")
    print("=" * 80)

    from fastapi.testclient import TestClient

    client = TestClient(app)

    # 1. 健康检查
    print("\n[Test 1] Health Check")
    response = client.get("/health")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")

    # 2. 登录获取 Token
    print("\n[Test 2] Login")
    login_data = {
        "username": "demo",
        "password": "demo123"
    }
    response = client.post("/v1/auth/login", json=login_data)
    print(f"  Status: {response.status_code}")
    result = response.json()
    access_token = result["access_token"]
    print(f"  Token: {access_token[:50]}...")
    print(f"  User: {result['user']['username']}")
    print(f"  Role: {result['user']['role']}")
    print(f"  Expires in: {result['expires_in']}s")

    # 3. 使用 Token 访问受保护端点
    print("\n[Test 3] Access Protected Endpoint with Token")
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/v1/auth/me", headers=headers)
    print(f"  Status: {response.status_code}")
    result = response.json()
    print(f"  User ID: {result['user_id']}")
    print(f"  Username: {result['username']}")
    print(f"  Role: {result['role']}")

    # 4. 使用 API Key 访问
    print("\n[Test 4] Access with API Key")
    api_key = "sk_test_demo_key_67890"
    headers = {"X-API-Key": api_key}
    response = client.get("/v1/auth/me", headers=headers)
    print(f"  Status: {response.status_code}")
    result = response.json()
    print(f"  Username: {result['username']}")

    # 5. 创建新的 API Key
    print("\n[Test 5] Create API Key")
    headers = {"Authorization": f"Bearer {access_token}"}
    api_key_data = {
        "name": "Test API Key",
        "description": "For testing"
    }
    response = client.post("/v1/auth/api-key", json=api_key_data, headers=headers)
    print(f"  Status: {response.status_code}")
    result = response.json()
    print(f"  API Key: {result['api_key'][:30]}...")
    print(f"  Name: {result['name']}")

    # 6. 获取速率限制信息
    print("\n[Test 6] Rate Limit Info")
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/v1/rate-limit", headers=headers)
    print(f"  Status: {response.status_code}")
    result = response.json()
    print(f"  Limit: {result['limit']}")
    print(f"  Remaining: {result['remaining']}")
    print(f"  Reset: {result['reset']}")

    # 7. 测试速率限制
    print("\n[Test 7] Test Rate Limiting")
    headers = {"Authorization": f"Bearer {access_token}"}
    success_count = 0
    rate_limited_count = 0

    for i in range(10):
        response = client.get("/v1/protected/example", headers=headers)
        if response.status_code == 200:
            success_count += 1
        elif response.status_code == 429:
            rate_limited_count += 1

    print(f"  Success: {success_count}")
    print(f"  Rate Limited: {rate_limited_count}")

    # 8. 未认证访问
    print("\n[Test 8] Unauthorized Access")
    response = client.get("/v1/auth/me")
    print(f"  Status: {response.status_code}")
    print(f"  Detail: {response.json()['detail']}")

    # 9. 错误的密码
    print("\n[Test 9] Wrong Password")
    login_data = {
        "username": "demo",
        "password": "wrong_password"
    }
    response = client.post("/v1/auth/login", json=login_data)
    print(f"  Status: {response.status_code}")
    print(f"  Detail: {response.json()['detail']}")


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
    print("Phase 4 Week 8 Day 7: Authentication, Rate Limiting, and API Documentation")
    print("=" * 80)

    # 运行演示
    asyncio.run(demo_auth_api())

    print("\n" + "=" * 80)
    print("All tests passed!")
    print("=" * 80)

    print("\n[Info] To run the server:")
    print("  uvicorn week8_day7_auth_gateway:app --reload --port 8000")
    print("\n[Info] API Documentation:")
    print("  Swagger UI: http://localhost:8000/docs")
    print("  ReDoc: http://localhost:8000/redoc")
    print("\n[Info] Test Credentials:")
    print("  Username: demo")
    print("  Password: demo123")
    print("  API Key: sk_test_demo_key_67890")


if __name__ == "__main__":
    main()
