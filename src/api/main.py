from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
import time
import re

from src.api.config import get_settings
from src.api.dependencies import get_engine
from src.api.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    register_exception_handlers,
    AuditMiddleware,
    SecureHeadersMiddleware,
)
from src.api.security import SensitiveDataFilter
from src.api.monitoring import (
    init_sentry,
    configure_logging,
    get_logger,
    MetricsMiddleware,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    record_error,
    capture_exception,
)
from src.api.routes.health import set_startup_time

# Configure structured logging
settings = get_settings()
configure_logging(
    log_level=settings.log_level,
    json_logs=settings.log_json and not settings.debug,
    add_caller_info=settings.debug
)
logger = get_logger(__name__)


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """
    Custom CORS middleware that:
    1. Supports dynamic origin patterns (regex) for Vercel subdomains
    2. Adds CORS headers to ALL responses, including errors (422, 500, etc.)
    3. Properly handles preflight OPTIONS requests
    """

    def __init__(self, app, settings):
        super().__init__(app)
        self.allowed_origins = set(settings.cors_origins)
        self.origin_patterns = [re.compile(p) for p in settings.cors_origin_patterns]
        self.allow_credentials = settings.cors_allow_credentials
        self.allow_methods = ", ".join(settings.cors_allow_methods)
        self.allow_headers = ", ".join(settings.cors_allow_headers)

    def is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed via static list or regex patterns."""
        if not origin:
            return False

        # Check static origins first (faster)
        if origin in self.allowed_origins:
            return True

        # Check regex patterns
        for pattern in self.origin_patterns:
            if pattern.match(origin):
                return True

        return False

    def add_cors_headers(self, response, origin: str):
        """Add CORS headers to response."""
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true" if self.allow_credentials else "false"
        response.headers["Access-Control-Allow-Methods"] = self.allow_methods
        response.headers["Access-Control-Allow-Headers"] = self.allow_headers
        response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
        return response

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        is_allowed = self.is_origin_allowed(origin)

        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            if is_allowed:
                response = Response(status_code=200)
                self.add_cors_headers(response, origin)
                # Add max age for preflight cache
                response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours
                return response
            else:
                # Origin not allowed - return 403
                return Response(status_code=403, content="Origin not allowed")

        # Process the actual request
        try:
            response = await call_next(request)
        except Exception as e:
            # On exceptions, return error response WITH CORS headers
            # This is critical - without CORS headers, browser won't show the error
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "error": str(e)}
            )
            if is_allowed:
                self.add_cors_headers(response, origin)
            return response  # Return instead of raise to ensure CORS headers are sent

        # Add CORS headers to all responses (success and error status codes)
        if is_allowed:
            self.add_cors_headers(response, origin)

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    settings = get_settings()

    # Initialize Sentry if configured
    if settings.sentry_dsn:
        sentry_initialized = init_sentry(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            debug=settings.debug
        )
        if sentry_initialized:
            logger.info("Sentry error tracking initialized",
                       environment=settings.environment)
        else:
            logger.warning("Failed to initialize Sentry")

    logger.info("Starting Taxdown API...",
               version=settings.app_version,
               environment=settings.environment,
               debug=settings.debug)

    engine = get_engine()
    logger.info("Connected to database")

    # Initialize Redis cache if configured
    if settings.cache_enabled and settings.redis_url:
        from src.api.cache import init_cache
        cache = init_cache(settings.redis_url)
        if cache.enabled:
            logger.info("Redis cache initialized", redis_url=settings.redis_url[:20] + "...")
        else:
            logger.warning("Redis cache initialization failed, caching disabled")
    else:
        logger.info("Caching disabled (no redis_url configured)")

    # Set startup time for uptime tracking
    set_startup_time()

    yield

    # Shutdown
    logger.info("Shutting down Taxdown API...")
    engine.dispose()
    logger.info("Database connections closed")


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

    # Custom CORS middleware with dynamic origin support and error response handling
    # This replaces the default CORSMiddleware to:
    # 1. Support regex patterns for Vercel subdomains (*.vercel.app)
    # 2. Ensure CORS headers are added to ALL responses including errors (422, 500)
    app.add_middleware(DynamicCORSMiddleware, settings=settings)

    # Rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_per_minute,
        burst_limit=settings.rate_limit_burst
    )

    # Request ID middleware
    app.add_middleware(RequestIDMiddleware)

    # Prometheus metrics middleware (must be added before other middleware)
    app.add_middleware(MetricsMiddleware)

    # Security middleware - Secure Headers
    if settings.enable_secure_headers:
        # Disable HSTS in development (no HTTPS)
        include_hsts = settings.enable_hsts and not settings.is_development
        app.add_middleware(
            SecureHeadersMiddleware,
            include_hsts=include_hsts,
            exclude_paths=["/docs", "/redoc", "/openapi.json"],
        )
        logger.info("Secure headers middleware enabled", hsts=include_hsts)

    # Security middleware - Audit Logging
    if settings.enable_audit_logging:
        app.add_middleware(
            AuditMiddleware,
            log_reads=settings.audit_log_reads,
            exclude_paths=["/health", "/ready", "/metrics", "/docs", "/redoc"],
        )
        logger.info("Audit logging middleware enabled", log_reads=settings.audit_log_reads)

    # Register exception handlers
    register_exception_handlers(app)

    # Request logging middleware with structured logging
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()

        # Get request ID if available
        request_id = getattr(request.state, "request_id", "unknown")

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Structured log with context
            logger.info(
                "Request completed",
                request_id=request_id[:8] if request_id != "unknown" else request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                client_ip=request.client.host if request.client else None,
            )
            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                request_id=request_id[:8] if request_id != "unknown" else request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                exc_info=True,
            )
            # Record error metric
            record_error(type(e).__name__, request.url.path)
            # Capture in Sentry
            capture_exception(e, request_id=request_id, path=request.url.path)
            raise

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
    from src.api.routes import properties, analysis, appeals, reports, portfolios, health
    app.include_router(health.router)  # Health endpoints at root level
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
