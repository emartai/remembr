"""API key management endpoints."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.api_key import APIKey
from app.models.user import User
from app.services.api_keys import create_api_key, revoke_api_key
from app.services.auth import get_current_user

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


# Request/Response Models
class CreateAPIKeyRequest(BaseModel):
    """Request model for creating an API key."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable name for the key")
    agent_id: uuid.UUID | None = Field(None, description="Optional agent ID to scope the key")
    expires_at: datetime | None = Field(None, description="Optional expiration datetime")


class CreateAPIKeyResponse(BaseModel):
    """Response model for API key creation."""
    
    id: uuid.UUID = Field(..., description="API key ID")
    name: str = Field(..., description="Key name")
    api_key: str = Field(..., description="Raw API key (shown only once)")
    org_id: uuid.UUID = Field(..., description="Organization ID")
    user_id: uuid.UUID | None = Field(None, description="User ID (if scoped)")
    agent_id: uuid.UUID | None = Field(None, description="Agent ID (if scoped)")
    expires_at: datetime | None = Field(None, description="Expiration datetime")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class APIKeyListItem(BaseModel):
    """Response model for API key list item."""
    
    id: uuid.UUID = Field(..., description="API key ID")
    name: str = Field(..., description="Key name")
    org_id: uuid.UUID = Field(..., description="Organization ID")
    user_id: uuid.UUID | None = Field(None, description="User ID (if scoped)")
    agent_id: uuid.UUID | None = Field(None, description="Agent ID (if scoped)")
    last_used_at: datetime | None = Field(None, description="Last usage timestamp")
    expires_at: datetime | None = Field(None, description="Expiration datetime")
    created_at: datetime = Field(..., description="Creation timestamp")
    is_expired: bool = Field(..., description="Whether the key is expired")
    
    class Config:
        from_attributes = True


class APIKeyListResponse(BaseModel):
    """Response model for API key list."""
    
    keys: list[APIKeyListItem] = Field(..., description="List of API keys")
    total: int = Field(..., description="Total number of keys")


@router.post("", response_model=CreateAPIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_new_api_key(
    request: CreateAPIKeyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CreateAPIKeyResponse:
    """
    Create a new API key.
    
    Requires JWT authentication. The raw API key is returned ONCE and never again.
    Store it securely - it cannot be retrieved later.
    
    Args:
        request: API key creation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        API key details including the raw key (shown only once)
    """
    # Create the API key
    api_key, raw_key = await create_api_key(
        db=db,
        org_id=current_user.org_id,
        name=request.name,
        user_id=current_user.id,
        agent_id=request.agent_id,
        expires_at=request.expires_at,
    )
    
    await db.commit()
    
    logger.info(
        "API key created via endpoint",
        key_id=str(api_key.id),
        user_id=str(current_user.id),
        org_id=str(current_user.org_id),
    )
    
    return CreateAPIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        api_key=raw_key,  # Only time raw key is returned
        org_id=api_key.org_id,
        user_id=api_key.user_id,
        agent_id=api_key.agent_id,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIKeyListResponse:
    """
    List all API keys for the current user's organization.
    
    Never returns raw API keys, only metadata.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of API keys with metadata
    """
    # Query all keys for the organization
    result = await db.execute(
        select(APIKey)
        .where(APIKey.org_id == current_user.org_id)
        .order_by(APIKey.created_at.desc())
    )
    api_keys = result.scalars().all()
    
    # Build response with expiration status
    now = datetime.now(datetime.now().astimezone().tzinfo)
    keys = [
        APIKeyListItem(
            id=key.id,
            name=key.name,
            org_id=key.org_id,
            user_id=key.user_id,
            agent_id=key.agent_id,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
            created_at=key.created_at,
            is_expired=key.expires_at is not None and key.expires_at <= now,
        )
        for key in api_keys
    ]
    
    logger.info(
        "API keys listed",
        org_id=str(current_user.org_id),
        count=len(keys),
    )
    
    return APIKeyListResponse(
        keys=keys,
        total=len(keys),
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key_endpoint(
    key_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> None:
    """
    Revoke an API key.
    
    Sets the expiration to now, effectively disabling the key.
    Also invalidates any cached lookups.
    
    Args:
        key_id: API key ID to revoke
        current_user: Current authenticated user
        db: Database session
        redis: Redis client
        
    Raises:
        HTTPException: If key not found or not authorized
    """
    # Revoke the key
    success = await revoke_api_key(
        db=db,
        redis=redis,
        key_id=key_id,
        org_id=current_user.org_id,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    await db.commit()
    
    logger.info(
        "API key revoked via endpoint",
        key_id=str(key_id),
        user_id=str(current_user.id),
        org_id=str(current_user.org_id),
    )
