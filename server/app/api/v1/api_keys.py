"""API key management endpoints."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from loguru import logger
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.responses import StandardResponse, success
from app.db.redis import get_redis
from app.db.session import get_db
from app.error_codes import API_KEY_NOT_FOUND
from app.exceptions import NotFoundError
from app.models.api_key import APIKey
from app.models.user import User
from app.services.api_keys import create_api_key, revoke_api_key
from app.services.auth import get_current_user

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    agent_id: uuid.UUID | None = None
    expires_at: datetime | None = None


class CreateAPIKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    api_key: str
    org_id: uuid.UUID
    user_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    expires_at: datetime | None = None
    created_at: datetime


class APIKeyListItem(BaseModel):
    id: uuid.UUID
    name: str
    org_id: uuid.UUID
    user_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    is_expired: bool


class APIKeyListResponse(BaseModel):
    keys: list[APIKeyListItem]
    total: int


@router.post(
    "",
    response_model=StandardResponse[CreateAPIKeyResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_new_api_key(
    payload: CreateAPIKeyRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StandardResponse[CreateAPIKeyResponse]:
    api_key, raw_key = await create_api_key(
        db=db,
        org_id=current_user.org_id,
        name=payload.name,
        user_id=current_user.id,
        agent_id=payload.agent_id,
        expires_at=payload.expires_at,
    )
    await db.commit()

    logger.info(
        "API key created via endpoint",
        key_id=str(api_key.id),
        user_id=str(current_user.id),
    )

    return success(
        CreateAPIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            api_key=raw_key,
            org_id=api_key.org_id,
            user_id=api_key.user_id,
            agent_id=api_key.agent_id,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
        ),
        request_id=request.state.request_id,
    )


@router.get("", response_model=StandardResponse[APIKeyListResponse])
async def list_api_keys(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StandardResponse[APIKeyListResponse]:
    result = await db.execute(
        select(APIKey)
        .where(APIKey.org_id == current_user.org_id)
        .order_by(APIKey.created_at.desc())
    )
    api_keys = result.scalars().all()

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
    return success(
        APIKeyListResponse(keys=keys, total=len(keys)),
        request_id=request.state.request_id,
    )


@router.delete("/{key_id}", response_model=StandardResponse[dict[str, str]])
async def revoke_api_key_endpoint(
    key_id: uuid.UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> StandardResponse[dict[str, str]]:
    ok = await revoke_api_key(db=db, redis=redis, key_id=key_id, org_id=current_user.org_id)
    if not ok:
        raise NotFoundError("API key not found", details={"code": API_KEY_NOT_FOUND})

    await db.commit()
    return success({"message": "API key revoked"}, request_id=request.state.request_id)
