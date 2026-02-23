"""Authentication endpoints for user registration, login, and token management."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, EmailStr, Field
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.redis import get_redis
from app.db.session import get_db
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


# Request/Response Models
class RegisterRequest(BaseModel):
    """Request model for user registration."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    org_name: str = Field(..., min_length=1, max_length=255, description="Organization name")


class LoginRequest(BaseModel):
    """Request model for user login."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Response model for token endpoints."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class RefreshRequest(BaseModel):
    """Request model for token refresh."""
    
    refresh_token: str = Field(..., description="JWT refresh token")


class RefreshResponse(BaseModel):
    """Response model for token refresh."""
    
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class UserResponse(BaseModel):
    """Response model for user information."""
    
    id: uuid.UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    org_id: uuid.UUID = Field(..., description="Organization ID")
    team_id: uuid.UUID | None = Field(None, description="Team ID (if assigned)")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: datetime = Field(..., description="User creation timestamp")
    
    class Config:
        from_attributes = True


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Register a new user and create an organization.
    
    For MVP, registering creates a new organization with the user as the first member.
    
    Args:
        request: Registration request with email, password, and org name
        db: Database session
        
    Returns:
        Access and refresh tokens
        
    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create organization
    org = Organization(name=request.org_name)
    db.add(org)
    await db.flush()  # Flush to get org.id
    
    # Create user
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        org_id=org.id,
        is_active=True,
    )
    db.add(user)
    await db.flush()  # Flush to get user.id
    
    await db.commit()
    
    logger.info(
        "User registered",
        user_id=str(user.id),
        email=user.email,
        org_id=str(org.id),
    )
    
    # Create tokens
    token_data = {"sub": str(user.id), "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Authenticate user and return access and refresh tokens.
    
    Args:
        request: Login request with email and password
        db: Database session
        
    Returns:
        Access and refresh tokens
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Fetch user
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info("User logged in", user_id=str(user.id), email=user.email)
    
    # Create tokens
    token_data = {"sub": str(user.id), "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: RefreshRequest,
    redis: Annotated[Redis, Depends(get_redis)],
) -> RefreshResponse:
    """
    Refresh access token using a valid refresh token.
    
    Args:
        request: Refresh request with refresh token
        redis: Redis client for checking invalidated tokens
        
    Returns:
        New access token
        
    Raises:
        HTTPException: If refresh token is invalid or invalidated
    """
    # Check if token is invalidated
    is_invalidated = await redis.get(f"invalidated_token:{request.refresh_token}")
    if is_invalidated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode and validate refresh token
    payload = decode_token(request.refresh_token)
    
    # Verify token type
    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user data
    user_id = payload.get("sub")
    email = payload.get("email")
    
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info("Token refreshed", user_id=user_id)
    
    # Create new access token
    token_data = {"sub": user_id, "email": email}
    access_token = create_access_token(token_data)
    
    return RefreshResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: RefreshRequest,
    redis: Annotated[Redis, Depends(get_redis)],
) -> None:
    """
    Logout user by invalidating their refresh token.
    
    The refresh token is stored in Redis with a TTL matching its expiration time.
    
    Args:
        request: Logout request with refresh token to invalidate
        redis: Redis client for storing invalidated tokens
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    # Decode token to get expiration
    payload = decode_token(request.refresh_token)
    
    # Verify token type
    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Calculate TTL (time until token expires)
    exp_timestamp = payload.get("exp")
    if exp_timestamp:
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        ttl_seconds = int((exp_datetime - datetime.now(timezone.utc)).total_seconds())
        
        # Only store if token hasn't expired yet
        if ttl_seconds > 0:
            await redis.setex(
                f"invalidated_token:{request.refresh_token}",
                ttl_seconds,
                "1",
            )
            
            user_id = payload.get("sub")
            logger.info("User logged out", user_id=user_id)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user from token
        
    Returns:
        User information (without password hash)
    """
    return UserResponse.model_validate(current_user)
