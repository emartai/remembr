import sys
import uuid
from contextlib import asynccontextmanager
from typing import Any

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import router as v1_router
from app.config import get_settings


def configure_logging() -> None:
    """Configure structured JSON logging with loguru."""
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Add JSON structured logging
    logger.add(
        sys.stdout,
        format="{extra[serialized]}",
        level=settings.log_level,
        serialize=True,
    )


def configure_sentry() -> None:
    """Initialize Sentry if DSN is configured."""
    settings = get_settings()
    
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn.get_secret_value(),
            environment=settings.environment,
            traces_sample_rate=1.0 if settings.environment == "local" else 0.1,
        )
        logger.info("Sentry initialized", environment=settings.environment)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    configure_logging()
    configure_sentry()
    
    # Initialize Redis
    from app.db.redis import init_redis
    
    try:
        await init_redis()
        logger.info("Application startup", version="0.1.0", redis="connected")
    except Exception as e:
        logger.error("Failed to initialize Redis", error=str(e))
        # Continue without Redis - endpoints will handle gracefully
        logger.warning("Application starting without Redis")
    
    yield
    
    # Shutdown
    from app.db.redis import close_redis
    
    await close_redis()
    logger.info("Application shutdown")


def create_app() -> FastAPI:
    """
    Application factory for creating configured FastAPI instances.
    
    Returns:
        Configured FastAPI application
    """
    settings = get_settings()
    
    app = FastAPI(
        title="Remembr API",
        description="Persistent memory infrastructure for AI agents",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_local else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request context middleware
    @app.middleware("http")
    async def add_request_context(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Import here to avoid circular dependency
        from app.middleware.context import get_current_context
        
        # Start with request_id in logger context
        log_context = {"request_id": request_id}
        
        with logger.contextualize(**log_context):
            logger.info(
                "Request started",
                method=request.method,
                path=request.url.path,
            )
            
            # Process request
            response = await call_next(request)
            
            # After request processing, check if we have auth context
            ctx = get_current_context()
            if ctx:
                # Update logger context with auth info
                log_context.update({
                    "org_id": str(ctx.org_id),
                    "user_id": str(ctx.user_id) if ctx.user_id else None,
                    "agent_id": str(ctx.agent_id) if ctx.agent_id else None,
                    "auth_method": ctx.auth_method,
                })
                
                # Add to response headers
                response.headers["X-Org-ID"] = str(ctx.org_id)
            
            response.headers["X-Request-ID"] = request_id
            
            # Log completion with full context
            with logger.contextualize(**log_context):
                logger.info(
                    "Request completed",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                )
            
            return response
    
    # Global exception handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.warning(
            "HTTP exception",
            request_id=request_id,
            status_code=exc.status_code,
            detail=exc.detail,
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                    "request_id": request_id,
                }
            },
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.warning(
            "Validation error",
            request_id=request_id,
            errors=exc.errors(),
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "request_id": request_id,
                    "details": exc.errors(),
                }
            },
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.error(
            "Unhandled exception",
            request_id=request_id,
            exception=str(exc),
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                }
            },
        )
    
    # Mount versioned API router
    app.include_router(v1_router, prefix=settings.api_v1_prefix)
    
    return app


# Create app instance
app = create_app()
