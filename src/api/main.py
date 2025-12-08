from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging

from src.api.config import get_settings
from src.api.dependencies import get_engine
from src.api.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    register_exception_handlers
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Taxdown API...")
    settings = get_settings()
    engine = get_engine()
    logger.info("Connected to database")
    logger.info(f"API version: {settings.app_version}")

    yield

    # Shutdown
    logger.info("Shutting down Taxdown API...")
    engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
        Taxdown API - Property Tax Intelligence Platform

        ## Features
        - Property search and details
        - Assessment fairness analysis
        - Appeal letter generation
        - Portfolio management
        - Report generation
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_per_minute,
        burst_limit=settings.rate_limit_burst
    )

    # Request ID middleware
    app.add_middleware(RequestIDMiddleware)

    # Register exception handlers
    register_exception_handlers(app)

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        # Include request ID in logs if available
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            f"[{request_id[:8]}] {request.method} {request.url.path} "
            f"- {response.status_code} - {duration:.3f}s"
        )
        return response

    # Health check endpoint
    @app.get("/health", tags=["System"])
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "version": settings.app_version}

    # Root endpoint
    @app.get("/", tags=["System"])
    async def root():
        """API root - returns basic info"""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
        }

    # Import and include routers
    from src.api.routes import properties, analysis, appeals, reports, portfolios
    app.include_router(properties.router, prefix="/api/v1")
    app.include_router(analysis.router, prefix="/api/v1")
    app.include_router(appeals.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")
    app.include_router(portfolios.router, prefix="/api/v1")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
