"""Example showing how to use JWT and API key authentication."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import User
from app.services.api_keys import get_api_key_auth
from app.services.auth import get_current_user

router = APIRouter(prefix="/examples", tags=["examples"])


# Example 1: JWT-only authentication
@router.get("/jwt-only")
async def jwt_only_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Endpoint that requires JWT authentication.

    Usage:
        curl -X GET http://localhost:8000/api/v1/examples/jwt-only \
          -H "Authorization: Bearer <access_token>"
    """
    return {
        "message": "Authenticated with JWT",
        "user_id": str(current_user.id),
        "email": current_user.email,
        "org_id": str(current_user.org_id),
    }


# Example 2: API key-only authentication
@router.get("/api-key-only")
async def api_key_only_endpoint(
    auth: Annotated[dict, Depends(get_api_key_auth)],
):
    """
    Endpoint that requires API key authentication.

    Usage:
        curl -X GET http://localhost:8000/api/v1/examples/api-key-only \
          -H "X-API-Key: rmbr_..."
    """
    return {
        "message": "Authenticated with API key",
        "org_id": str(auth["org_id"]),
        "user_id": str(auth["user_id"]) if auth["user_id"] else None,
        "agent_id": str(auth["agent_id"]) if auth["agent_id"] else None,
        "key_id": str(auth["key_id"]),
    }


# Example 3: Accept either JWT or API key
async def get_flexible_auth(
    jwt_user: Annotated[User | None, Depends(get_current_user)] = None,
    api_key_auth: Annotated[dict | None, Depends(get_api_key_auth)] = None,
) -> dict:
    """
    Flexible authentication that accepts either JWT or API key.

    Returns a normalized auth context with org_id and optional user_id.
    """
    if jwt_user:
        return {
            "auth_type": "jwt",
            "org_id": jwt_user.org_id,
            "user_id": jwt_user.id,
            "agent_id": None,
        }
    elif api_key_auth:
        return {
            "auth_type": "api_key",
            "org_id": api_key_auth["org_id"],
            "user_id": api_key_auth["user_id"],
            "agent_id": api_key_auth["agent_id"],
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (JWT or API key)",
        )


@router.get("/flexible")
async def flexible_endpoint(
    auth: Annotated[dict, Depends(get_flexible_auth)],
):
    """
    Endpoint that accepts either JWT or API key authentication.

    Usage with JWT:
        curl -X GET http://localhost:8000/api/v1/examples/flexible \
          -H "Authorization: Bearer <access_token>"

    Usage with API key:
        curl -X GET http://localhost:8000/api/v1/examples/flexible \
          -H "X-API-Key: rmbr_..."
    """
    return {
        "message": f"Authenticated with {auth['auth_type']}",
        "org_id": str(auth["org_id"]),
        "user_id": str(auth["user_id"]) if auth["user_id"] else None,
        "agent_id": str(auth["agent_id"]) if auth["agent_id"] else None,
    }


# Example 4: Organization-scoped data access
@router.get("/org-data")
async def org_data_endpoint(
    auth: Annotated[dict, Depends(get_flexible_auth)],
):
    """
    Example showing how to use auth context for org-scoped queries.

    Both JWT and API key authentication provide org_id for scoping.
    """
    org_id = auth["org_id"]

    # In a real endpoint, you would query data scoped to org_id
    # Example:
    # result = await db.execute(
    #     select(SomeModel).where(SomeModel.org_id == org_id)
    # )

    return {
        "message": "Data scoped to organization",
        "org_id": str(org_id),
        "auth_type": auth["auth_type"],
        "note": "All queries should be scoped to org_id for multi-tenancy",
    }
