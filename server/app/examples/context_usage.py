"""Example usage of request context middleware."""

from typing import Annotated

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middleware.context import RequestContext, get_current_context, require_auth

router = APIRouter()


@router.get("/example/protected")
async def protected_endpoint(
    ctx: Annotated[RequestContext, Depends(require_auth)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Example protected endpoint that requires authentication.
    
    The require_auth dependency ensures the user is authenticated via
    JWT or API key. The context contains org_id, user_id, and agent_id.
    
    The get_db dependency automatically sets the org context for RLS.
    """
    logger.info(
        "Protected endpoint accessed",
        org_id=str(ctx.org_id),
        user_id=str(ctx.user_id) if ctx.user_id else None,
        auth_method=ctx.auth_method,
    )
    
    return {
        "message": "Access granted",
        "org_id": str(ctx.org_id),
        "user_id": str(ctx.user_id) if ctx.user_id else None,
        "agent_id": str(ctx.agent_id) if ctx.agent_id else None,
        "auth_method": ctx.auth_method,
    }


@router.get("/example/optional-auth")
async def optional_auth_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Example endpoint with optional authentication.
    
    Uses get_current_context() to check if user is authenticated
    without requiring it.
    """
    ctx = get_current_context()
    
    if ctx:
        logger.info(
            "Optional auth endpoint accessed with auth",
            org_id=str(ctx.org_id),
        )
        return {
            "message": "Authenticated access",
            "org_id": str(ctx.org_id),
            "authenticated": True,
        }
    else:
        logger.info("Optional auth endpoint accessed without auth")
        return {
            "message": "Anonymous access",
            "authenticated": False,
        }


@router.get("/example/context-anywhere")
async def context_anywhere_endpoint(
    ctx: Annotated[RequestContext, Depends(require_auth)],
):
    """
    Example showing context is accessible anywhere in the call stack.
    
    The context is stored in contextvars, so you can access it from
    any function without passing it explicitly.
    """
    # Call a helper function that accesses context
    result = _helper_function()
    
    return {
        "message": "Context accessible everywhere",
        "from_dependency": str(ctx.org_id),
        "from_helper": result,
    }


def _helper_function() -> dict:
    """
    Helper function that accesses context without it being passed.
    
    This demonstrates that context is available anywhere in the call stack
    via contextvars, not just in the endpoint function.
    """
    ctx = get_current_context()
    
    if ctx:
        logger.info(
            "Helper function accessed context",
            org_id=str(ctx.org_id),
        )
        return {
            "org_id": str(ctx.org_id),
            "auth_method": ctx.auth_method,
        }
    
    return {"error": "No context available"}


# Example of using context in a service function
async def example_service_function(db: AsyncSession):
    """
    Example service function that uses context.
    
    Service functions can access the request context without it being
    passed as a parameter.
    """
    ctx = get_current_context()
    
    if not ctx:
        raise ValueError("No authentication context available")
    
    logger.info(
        "Service function executing",
        org_id=str(ctx.org_id),
        user_id=str(ctx.user_id) if ctx.user_id else None,
    )
    
    # The db session already has org context set via RLS
    # All queries are automatically scoped to ctx.org_id
    
    # Your business logic here
    return {
        "org_id": str(ctx.org_id),
        "processed": True,
    }
