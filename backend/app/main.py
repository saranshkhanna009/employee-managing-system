"""FastAPI application factory."""

import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db, close_db
from app.api.v1 import auth, company, departments, employees, tasks, daily_logs, leaves, audit, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Employee Tracking System",
        description="Secure multi-company employee tracking with field-level encryption",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    )

    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Security headers middleware
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # CSP
        response.headers["Content-Security-Policy"] = settings.CSP_POLICY

        # HSTS (only in production with HTTPS)
        if settings.ENVIRONMENT == "production" and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains; preload"

        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]

        return response

    # Request ID middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Audit logging middleware
    @app.middleware("http")
    async def audit_logging_middleware(request: Request, call_next):
        # Skip audit for health checks and static files
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"):
            return await call_next(request)

        response = await call_next(request)

        # Log API access (non-sensitive)
        if request.url.path.startswith("/api/"):
            # We can't easily get employee here without session validation
            # This would be done in individual route handlers
            pass

        return response

    # Exception handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": 422,
                    "message": "Validation error",
                    "details": exc.errors(),
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        # Log the exception (in production, use proper logging)
        import traceback
        traceback.print_exc()

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": 500,
                    "message": "Internal server error" if not settings.DEBUG else str(exc),
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    # Health check endpoint
    @app.get("/health", include_in_schema=False)
    async def health_check():
        return {"status": "healthy", "version": "1.0.0"}

    # Include API routers
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(company.router, prefix="/api/v1")
    app.include_router(departments.router, prefix="/api/v1")
    app.include_router(employees.router, prefix="/api/v1")
    app.include_router(tasks.router, prefix="/api/v1")
    app.include_router(daily_logs.router, prefix="/api/v1")
    app.include_router(leaves.router, prefix="/api/v1")
    app.include_router(audit.router, prefix="/api/v1")
    app.include_router(analytics.router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    )
