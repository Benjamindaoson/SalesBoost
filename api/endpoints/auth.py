"""
Authentication API Endpoints
"""
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.database import get_db_session
from models.saas_models import User as DBUser
from api.auth_schemas import Token, UserSchema
from api.auth_utils import verify_password, create_access_token
from api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()

@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
):
    username = form_data.username
    password = form_data.password

    if settings.ADMIN_USERNAME and username == settings.ADMIN_USERNAME:
        if settings.ADMIN_PASSWORD_HASH:
            if not verify_password(password, settings.ADMIN_PASSWORD_HASH):
                raise HTTPException(status_code=401, detail="Incorrect username or password")
        elif settings.ADMIN_PASSWORD and settings.ALLOW_INSECURE_ADMIN_PASSWORD:
            if password != settings.ADMIN_PASSWORD:
                raise HTTPException(status_code=401, detail="Incorrect username or password")
        else:
            raise HTTPException(status_code=500, detail="Admin password not configured securely")
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username, "role": "admin", "tenant_id": None},
            expires_delta=access_token_expires,
        )
        logger.info("System Admin logged in: %s", username)
        return {"access_token": access_token, "token_type": "bearer"}

    result = await db.execute(
        select(DBUser).where((DBUser.username == username) | (DBUser.email == username))
    )
    db_user = result.scalar_one_or_none()

    if db_user and verify_password(password, db_user.hashed_password):
        if not db_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": db_user.username,
                "role": db_user.role,
                "tenant_id": db_user.tenant_id,
                "user_id": db_user.id,
            },
            expires_delta=access_token_expires,
        )
        logger.info("SaaS User logged in: %s (Tenant: %s)", username, db_user.tenant_id)
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: UserSchema = Depends(get_current_user)):
    return current_user
