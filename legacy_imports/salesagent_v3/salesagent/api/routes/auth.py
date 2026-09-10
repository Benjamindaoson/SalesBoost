"""Authentication API endpoints."""
from __future__ import annotations

from datetime import timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from salesagent.auth.jwt import create_access_token, verify_password, get_password_hash
from salesagent.core.settings import settings
from salesagent.dependencies import get_db

log = structlog.get_logger()

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str
    expires_in: int


class RegisterRequest(BaseModel):
    """User registration request model."""
    username: str
    password: str
    email: str | None = None


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Login endpoint - authenticate user and return JWT token.

    Args:
        request: Login credentials
        db: Database session

    Returns:
        JWT access token and metadata

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # TODO: Implement proper user authentication from database
    # For now, use hardcoded admin user for testing

    # Hardcoded users for MVP (REMOVE IN PRODUCTION)
    HARDCODED_USERS = {
        "admin": {
            "password_hash": get_password_hash("admin123"),
            "role": "admin",
            "user_id": "admin-001",
        },
        "user": {
            "password_hash": get_password_hash("user123"),
            "role": "user",
            "user_id": "user-001",
        },
    }

    user_data = HARDCODED_USERS.get(request.username)

    if not user_data or not verify_password(request.password, user_data["password_hash"]):
        log.warning("Failed login attempt", username=request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT token
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    token_data = {
        "sub": request.username,
        "user_id": user_data["user_id"],
        "role": user_data["role"],
    }
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)

    log.info("User logged in", username=request.username, role=user_data["role"])

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/register")
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    User registration endpoint (placeholder for future implementation).

    Args:
        request: Registration data
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 501 Not Implemented
    """
    # TODO: Implement user registration
    # 1. Validate username/email uniqueness
    # 2. Hash password
    # 3. Create user record in database
    # 4. Return success or error

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User registration not yet implemented",
    )


@router.post("/refresh")
async def refresh_token(
    current_user: dict = Depends(get_db),
) -> LoginResponse:
    """
    Refresh JWT token endpoint (placeholder for future implementation).

    Args:
        current_user: Current authenticated user

    Returns:
        New JWT token

    Raises:
        HTTPException: 501 Not Implemented
    """
    # TODO: Implement token refresh
    # 1. Verify refresh token
    # 2. Issue new access token
    # 3. Optionally rotate refresh token

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh not yet implemented",
    )
