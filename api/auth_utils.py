import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models.saas_models import User as DBUser
from api.auth_schemas import UserSchema

logger = logging.getLogger(__name__)
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Bcrypt has a 72-byte limit, truncate if necessary
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    # Bcrypt has a 72-byte limit, truncate if necessary
    if len(password.encode('utf-8')) > 72:
        password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    if not settings.SECRET_KEY:
        raise HTTPException(status_code=500, detail="Server misconfigured: SECRET_KEY not set")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user_from_token(token: str, db: AsyncSession) -> UserSchema:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not settings.SECRET_KEY:
        raise HTTPException(status_code=500, detail="Server misconfigured: SECRET_KEY not set")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        payload.get("role", "student")
        payload.get("tenant_id")
        user_id: str = payload.get("user_id")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Always validate against DB for production security
    if user_id:
        result = await db.execute(select(DBUser).where(DBUser.id == user_id))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            # Token valid but user deleted/not found
            raise credentials_exception
            
        if not db_user.is_active:
                raise HTTPException(status_code=400, detail="Inactive user")
                
        return UserSchema(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            role=db_user.role,
            tenant_id=db_user.tenant_id,
        )
    
    # If we got here with just username but no user_id (old tokens?), also force DB check
    # or reject if policy demands. For now, we reject if no DB match found above when user_id expected.
    # But if the logic falls through (e.g. legacy token without user_id?), 
    # we MUST NOT return a schema blind.
    
    # Fallback lookup by username if user_id was missing but username present
    if username:
        result = await db.execute(select(DBUser).where(DBUser.username == username))
        db_user = result.scalar_one_or_none()
        if not db_user:
            raise credentials_exception
            
        return UserSchema(
            id=db_user.id,
            username=db_user.username,
            role=db_user.role,
            tenant_id=db_user.tenant_id
        )

    raise credentials_exception


