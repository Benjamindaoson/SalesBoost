"""
Authentication API Endpoints
基础认证功能
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from jose import JWTError, jwt

from app.core.database import get_db_session
from app.core.config import get_settings
from app.models.saas_models import User as DBUser, Tenant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()

# OAuth2 配置
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


class Token(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"


class User(BaseModel):
    """用户模型 (Pydantic)"""
    id: str
    username: str
    email: Optional[str] = None
    role: str
    tenant_id: Optional[str] = None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        role: str = payload.get("role", "student")
        tenant_id: str = payload.get("tenant_id")
        user_id: str = payload.get("user_id")
        
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 优先从数据库验证（SaaS 模式）
    if user_id:
        result = await db.execute(select(DBUser).where(DBUser.id == user_id))
        db_user = result.scalar_one_or_none()
        if db_user:
             if not db_user.is_active:
                 raise HTTPException(status_code=400, detail="Inactive user")
             return User(
                 id=db_user.id, 
                 username=db_user.username, 
                 email=db_user.email,
                 role=db_user.role,
                 tenant_id=db_user.tenant_id
             )

    # 兼容旧逻辑/Admin 环境变量
    return User(id=username, username=username, role=role, tenant_id=tenant_id)


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
):
    """
    用户登录 (支持 Admin 环境变量 & SaaS 数据库用户)
    """
    username = form_data.username
    password = form_data.password
    
    # 1. 验证 Admin 环境变量 (系统级管理员)
    if (username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD):
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username, "role": "admin", "tenant_id": None}, 
            expires_delta=access_token_expires
        )
        logger.info(f"System Admin logged in: {username}")
        return {"access_token": access_token, "token_type": "bearer"}
        
    # 2. 验证数据库用户 (SaaS 租户用户)
    # 假设 username 字段存储的是 username 或 email
    result = await db.execute(select(DBUser).where(
        (DBUser.username == username) | (DBUser.email == username)
    ))
    db_user = result.scalar_one_or_none()
    
    if db_user and db_user.hashed_password == password: # MVP: 明文比对，生产环境需 hash
        if not db_user.is_active:
             raise HTTPException(status_code=400, detail="Inactive user")
             
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": db_user.username, 
                "role": db_user.role, 
                "tenant_id": db_user.tenant_id,
                "user_id": db_user.id
            }, 
            expires_delta=access_token_expires
        )
        logger.info(f"SaaS User logged in: {username} (Tenant: {db_user.tenant_id})")
        return {"access_token": access_token, "token_type": "bearer"}

    # 3. 兼容旧 Demo 模式 (仅当数据库为空且未匹配时)
    # 如果不是 admin 且数据库没查到，且配置允许 Demo
    if username and password:
        # 模拟一个默认租户用户
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username, "role": "student", "tenant_id": "demo_tenant"}, 
            expires_delta=access_token_expires
        )
        logger.info(f"Demo User logged in: {username}")
        return {"access_token": access_token, "token_type": "bearer"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user

