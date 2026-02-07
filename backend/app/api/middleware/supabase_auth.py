"""
Supabase Authentication Middleware

统一前后端认证：使用Supabase JWT验证

Author: Claude (Anthropic)
Date: 2026-02-05
"""

import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel


class User(BaseModel):
    """用户模型"""
    id: str
    email: str
    role: str = "user"
    metadata: dict = {}


class SupabaseAuth:
    """
    Supabase认证管理器

    验证Supabase JWT tokens并提取用户信息
    """

    def __init__(self):
        """初始化"""
        self.jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        self.supabase_url = os.getenv("SUPABASE_URL")

        if not self.jwt_secret:
            raise ValueError(
                "SUPABASE_JWT_SECRET environment variable is required. "
                "Get it from your Supabase project settings."
            )

        self.security = HTTPBearer()

    def verify_token(self, token: str) -> Optional[dict]:
        """
        验证JWT token

        Args:
            token: JWT token string

        Returns:
            Decoded token payload or None if invalid

        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Decode JWT
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
    ) -> User:
        """
        获取当前用户

        从JWT token中提取用户信息

        Args:
            credentials: HTTP Authorization credentials

        Returns:
            User object

        Raises:
            HTTPException: If authentication fails
        """
        token = credentials.credentials

        # Verify token
        payload = self.verify_token(token)

        # Extract user info
        user = User(
            id=payload.get("sub"),
            email=payload.get("email", ""),
            role=payload.get("role", "user"),
            metadata=payload.get("user_metadata", {}),
        )

        return user


# Global instance
supabase_auth = SupabaseAuth()


# Dependency for route protection
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> User:
    """
    FastAPI dependency for getting current user

    Usage:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id, "email": user.email}
    """
    return await supabase_auth.get_current_user(credentials)


# Optional: Admin-only dependency
async def get_current_admin_user(
    user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency for admin-only routes

    Usage:
        @app.delete("/admin/users/{user_id}")
        async def delete_user(
            user_id: str,
            admin: User = Depends(get_current_admin_user)
        ):
            # Only admins can access this
            pass
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return user
