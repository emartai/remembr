"""Authentication endpoints for user registration, login, and token management."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from loguru import logger
from pydantic import BaseModel, EmailStr, Field
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.responses import StandardResponse, success
from app.config import get_settings
from app.db.redis import get_redis
from app.db.session import get_db
from app.error_codes import (
    EMAIL_ALREADY_REGISTERED,
    INACTIVE_USER,
    INVALID_CREDENTIALS,
    INVALID_TOKEN_PAYLOAD,
    INVALID_TOKEN_TYPE,
    TOKEN_INVALIDATED,
)
from app.exceptions import AuthenticationError, ConflictError
from app.models.organization import Organization
from app.models.user import User
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    org_name: str = Field(..., min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID
    email: str
    org_id: uuid.UUID
    team_id: uuid.UUID | None
    is_active: bool
    created_at: datetime


@router.post(
    "/register",
    response_model=StandardResponse[TokenResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StandardResponse[TokenResponse]:
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise ConflictError("Email already registered", details={"code": EMAIL_ALREADY_REGISTERED})

    org = Organization(name=payload.org_name)
    db.add(org)
    await db.flush()

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        org_id=org.id,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.commit()

    logger.info("User registered", user_id=str(user.id), email=user.email)

    token_data = {"sub": str(user.id), "email": user.email}
    return success(
        TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        ),
        request_id=request.state.request_id,
    )


@router.post("/login", response_model=StandardResponse[TokenResponse])
async def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StandardResponse[TokenResponse]:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise AuthenticationError(
            "Incorrect email or password",
            details={"code": INVALID_CREDENTIALS},
        )
    if not user.is_active:
        raise AuthenticationError("Inactive user", details={"code": INACTIVE_USER})

    token_data = {"sub": str(user.id), "email": user.email}
    return success(
        TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        ),
        request_id=request.state.request_id,
    )


@router.post("/refresh", response_model=StandardResponse[RefreshResponse])
async def refresh(
    payload: RefreshRequest,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis)],
) -> StandardResponse[RefreshResponse]:
    if await redis.get(f"invalidated_token:{payload.refresh_token}"):
        raise AuthenticationError("Token has been invalidated", details={"code": TOKEN_INVALIDATED})

    data = decode_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise AuthenticationError("Invalid token type", details={"code": INVALID_TOKEN_TYPE})

    user_id = data.get("sub")
    email = data.get("email")
    if not user_id or not email:
        raise AuthenticationError("Invalid token payload", details={"code": INVALID_TOKEN_PAYLOAD})

    return success(
        RefreshResponse(access_token=create_access_token({"sub": user_id, "email": email})),
        request_id=request.state.request_id,
    )


@router.post("/logout", response_model=StandardResponse[dict[str, str]])
async def logout(
    payload: RefreshRequest,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis)],
) -> StandardResponse[dict[str, str]]:
    data = decode_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise AuthenticationError("Invalid token type", details={"code": INVALID_TOKEN_TYPE})

    exp_timestamp = data.get("exp")
    if exp_timestamp:
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=UTC)
        ttl_seconds = int((exp_datetime - datetime.now(UTC)).total_seconds())
        if ttl_seconds > 0:
            await redis.setex(f"invalidated_token:{payload.refresh_token}", ttl_seconds, "1")

    return success({"message": "Logged out"}, request_id=request.state.request_id)


@router.get("/me", response_model=StandardResponse[UserResponse])
async def get_me(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> StandardResponse[UserResponse]:
    return success(UserResponse.model_validate(current_user), request_id=request.state.request_id)
