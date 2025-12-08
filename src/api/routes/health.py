"""
Health check endpoints for the Taxdown API.

Provides:
- Basic health check
- Detailed health check with dependency status
- Prometheus metrics endpoint
- Readiness and liveness probes for Kubernetes
"""

import time
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import text

from src.api.config import get_settings, APISettings
from src.api.dependencies import get_db


router = APIRouter(tags=["Health"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class HealthStatus(BaseModel):
    """Basic health check response."""
    status: str
    timestamp: float
    version: str


class DependencyCheck(BaseModel):
    """Individual dependency check result."""
    status: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class DetailedHealthStatus(BaseModel):
    """Detailed health check response with dependency status."""
    status: str
    checks: Dict[str, DependencyCheck]
    timestamp: float
    version: str
    uptime_seconds: Optional[float] = None


# Track startup time for uptime calculation
_startup_time: Optional[float] = None


def set_startup_time():
    """Set the startup time (call during app startup)."""
    global _startup_time
    _startup_time = time.time()


def get_uptime() -> Optional[float]:
    """Get uptime in seconds."""
    if _startup_time is None:
        return None
    return time.time() - _startup_time


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@router.get("/health", response_model=HealthStatus)
async def health_check(settings: APISettings = Depends(get_settings)):
    """
    Basic health check endpoint.

    Returns a simple healthy status. Use this for load balancer health checks
    where you only need to know if the service is running.
    """
    return HealthStatus(
        status="healthy",
        timestamp=time.time(),
        version=settings.app_version
    )


@router.get("/health/live", response_model=HealthStatus)
async def liveness_probe(settings: APISettings = Depends(get_settings)):
    """
    Kubernetes liveness probe.

    Returns healthy if the application is running. This should NOT check
    external dependencies - if the app is alive, return healthy.
    """
    return HealthStatus(
        status="healthy",
        timestamp=time.time(),
        version=settings.app_version
    )


@router.get("/health/ready", response_model=DetailedHealthStatus)
async def readiness_probe(
    db=Depends(get_db),
    settings: APISettings = Depends(get_settings)
):
    """
    Kubernetes readiness probe.

    Returns healthy only if the application can accept traffic, meaning
    all critical dependencies (database) are available.
    """
    checks = {}

    # Database check (critical)
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        checks["database"] = DependencyCheck(
            status="healthy",
            latency_ms=round((time.time() - start) * 1000, 2)
        )
    except Exception as e:
        checks["database"] = DependencyCheck(
            status="unhealthy",
            error=str(e)
        )

    # Determine overall status
    all_healthy = all(c.status == "healthy" for c in checks.values())

    return DetailedHealthStatus(
        status="healthy" if all_healthy else "unhealthy",
        checks=checks,
        timestamp=time.time(),
        version=settings.app_version,
        uptime_seconds=get_uptime()
    )


@router.get("/health/detailed", response_model=DetailedHealthStatus)
async def detailed_health_check(
    db=Depends(get_db),
    settings: APISettings = Depends(get_settings)
):
    """
    Detailed health check with all dependency status.

    Checks:
    - Database connectivity and latency
    - Redis connectivity (if configured)
    - External API availability (if configured)

    Use this for debugging and monitoring dashboards.
    """
    checks = {}

    # Database check
    try:
        start = time.time()
        result = db.execute(text("SELECT 1"))
        result.close()
        latency = (time.time() - start) * 1000

        # Also check PostGIS if available
        postgis_version = None
        try:
            result = db.execute(text("SELECT PostGIS_Version()"))
            postgis_version = result.scalar()
            result.close()
        except Exception:
            pass

        checks["database"] = DependencyCheck(
            status="healthy",
            latency_ms=round(latency, 2),
            details={"postgis_version": postgis_version} if postgis_version else None
        )
    except Exception as e:
        checks["database"] = DependencyCheck(
            status="unhealthy",
            error=str(e)
        )

    # Redis check (if configured)
    redis_url = getattr(settings, 'redis_url', None)
    if redis_url:
        try:
            import redis
            start = time.time()
            r = redis.from_url(redis_url, socket_timeout=2)
            r.ping()
            checks["redis"] = DependencyCheck(
                status="healthy",
                latency_ms=round((time.time() - start) * 1000, 2)
            )
        except ImportError:
            checks["redis"] = DependencyCheck(
                status="unknown",
                error="redis package not installed"
            )
        except Exception as e:
            checks["redis"] = DependencyCheck(
                status="unhealthy",
                error=str(e)
            )

    # Claude API check (if enabled)
    if settings.enable_claude_api:
        claude_api_key = getattr(settings, 'claude_api_key', None)
        if claude_api_key:
            checks["claude_api"] = DependencyCheck(
                status="configured",
                details={"enabled": True}
            )
        else:
            checks["claude_api"] = DependencyCheck(
                status="not_configured",
                details={"enabled": True, "key_present": False}
            )

    # Determine overall status
    critical_checks = ["database"]
    critical_healthy = all(
        checks.get(c, DependencyCheck(status="unknown")).status == "healthy"
        for c in critical_checks
        if c in checks
    )
    all_healthy = all(c.status == "healthy" for c in checks.values())

    if critical_healthy and all_healthy:
        status = "healthy"
    elif critical_healthy:
        status = "degraded"
    else:
        status = "unhealthy"

    return DetailedHealthStatus(
        status=status,
        checks=checks,
        timestamp=time.time(),
        version=settings.app_version,
        uptime_seconds=get_uptime()
    )


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format. Configure your Prometheus
    scraper to collect from this endpoint.
    """
    from src.api.monitoring import get_metrics_response
    return get_metrics_response()


@router.get("/health/info")
async def health_info(settings: APISettings = Depends(get_settings)):
    """
    Return application information for debugging.

    Note: This endpoint may expose sensitive configuration in debug mode.
    Consider restricting access in production.
    """
    info = {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production",
        "features": {
            "claude_api": settings.enable_claude_api,
            "bulk_operations": settings.enable_bulk_operations,
            "api_key_required": settings.require_api_key,
        },
        "limits": {
            "rate_limit_per_minute": settings.rate_limit_per_minute,
            "max_bulk_properties": settings.max_bulk_properties,
            "max_page_size": settings.max_page_size,
        },
        "uptime_seconds": get_uptime(),
        "timestamp": time.time(),
    }

    return info


@router.get("/health/cache")
async def cache_stats(settings: APISettings = Depends(get_settings)):
    """
    Return cache statistics.

    Shows cache hit/miss rates, connected clients, and cache status.
    """
    from src.api.cache import get_cache_manager

    cache = get_cache_manager()
    stats = cache.get_stats()

    return {
        "cache_enabled": settings.cache_enabled,
        "redis_configured": settings.redis_url is not None,
        **stats,
        "timestamp": time.time(),
    }
