"""
Monitoring and observability for the Taxdown API.

Provides:
- Sentry error tracking
- Prometheus metrics
- Structured logging with structlog
"""

import time
from typing import Optional, Callable
from functools import wraps

import structlog
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST


# ============================================================================
# SENTRY INITIALIZATION
# ============================================================================

def init_sentry(dsn: str, environment: str = "production", debug: bool = False):
    """
    Initialize Sentry error tracking.

    Args:
        dsn: Sentry DSN (Data Source Name)
        environment: Environment name (production, staging, development)
        debug: Enable debug mode
    """
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                LoggingIntegration(
                    level=None,  # Capture all levels
                    event_level=None,  # Send errors as events
                ),
            ],
            environment=environment,
            traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
            profiles_sample_rate=0.1,  # 10% of transactions for profiling
            debug=debug,
            send_default_pii=False,  # Don't send PII by default
        )
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"Failed to initialize Sentry: {e}")
        return False


# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

# Request metrics
REQUEST_COUNT = Counter(
    "taxdown_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "taxdown_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

REQUEST_IN_PROGRESS = Gauge(
    "taxdown_requests_in_progress",
    "Number of requests currently in progress",
    ["method", "endpoint"]
)

# Business metrics
ANALYSIS_COUNT = Counter(
    "taxdown_analyses_total",
    "Total property analyses performed",
    ["recommendation"]
)

ANALYSIS_LATENCY = Histogram(
    "taxdown_analysis_latency_seconds",
    "Property analysis latency in seconds",
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
)

APPEAL_COUNT = Counter(
    "taxdown_appeals_total",
    "Total appeals generated",
    ["style"]
)

APPEAL_LATENCY = Histogram(
    "taxdown_appeal_latency_seconds",
    "Appeal generation latency in seconds",
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

PROPERTY_SEARCH_COUNT = Counter(
    "taxdown_property_searches_total",
    "Total property searches",
    ["search_type"]
)

PORTFOLIO_COUNT = Gauge(
    "taxdown_portfolios_total",
    "Total number of portfolios"
)

# Database metrics
DB_QUERY_LATENCY = Histogram(
    "taxdown_db_query_latency_seconds",
    "Database query latency in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

DB_CONNECTIONS_ACTIVE = Gauge(
    "taxdown_db_connections_active",
    "Number of active database connections"
)

# Error metrics
ERROR_COUNT = Counter(
    "taxdown_errors_total",
    "Total errors",
    ["error_type", "endpoint"]
)


def get_metrics_response():
    """Generate Prometheus metrics response."""
    from fastapi.responses import Response
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================================================
# STRUCTURED LOGGING
# ============================================================================

def configure_logging(
    log_level: str = "INFO",
    json_logs: bool = True,
    add_caller_info: bool = True
):
    """
    Configure structured logging with structlog.

    Args:
        log_level: Minimum log level
        json_logs: Output logs as JSON (recommended for production)
        add_caller_info: Add file/line information to logs
    """
    import logging

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
    )

    # Build processor chain
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if add_caller_info:
        processors.append(structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ))

    # Add final renderer
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None):
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# ============================================================================
# MONITORING MIDDLEWARE
# ============================================================================

class MetricsMiddleware:
    """
    Middleware to collect request metrics.

    Tracks:
    - Request count by method, endpoint, status
    - Request latency by method, endpoint
    - Requests in progress
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        # Normalize path to avoid high cardinality
        endpoint = self._normalize_path(path)

        # Track in-progress requests
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()

        start_time = time.time()
        status_code = 500  # Default to error

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Record metrics
            duration = time.time() - start_time

            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=str(status_code)
            ).inc()

            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path to reduce cardinality.

        Replaces UUIDs and numeric IDs with placeholders.
        """
        import re

        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path,
            flags=re.IGNORECASE
        )

        # Replace numeric IDs in path segments
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)

        # Replace parcel IDs (format: XXX-XXX-XXXXX)
        path = re.sub(r'/\d{3}-\d{3}-\d{5}(?=/|$)', '/{parcel_id}', path)

        return path


# ============================================================================
# TIMING DECORATORS
# ============================================================================

def track_analysis_time(func: Callable) -> Callable:
    """Decorator to track analysis execution time."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            ANALYSIS_LATENCY.observe(time.time() - start)

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            ANALYSIS_LATENCY.observe(time.time() - start)

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def track_appeal_time(func: Callable) -> Callable:
    """Decorator to track appeal generation time."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            APPEAL_LATENCY.observe(time.time() - start)

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            APPEAL_LATENCY.observe(time.time() - start)

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def track_db_query(operation: str):
    """Context manager to track database query time."""
    class DBQueryTracker:
        def __init__(self, operation: str):
            self.operation = operation
            self.start = None

        def __enter__(self):
            self.start = time.time()
            return self

        def __exit__(self, *args):
            DB_QUERY_LATENCY.labels(operation=self.operation).observe(
                time.time() - self.start
            )

    return DBQueryTracker(operation)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def record_analysis(recommendation: str):
    """Record an analysis metric."""
    ANALYSIS_COUNT.labels(recommendation=recommendation).inc()


def record_appeal(style: str):
    """Record an appeal generation metric."""
    APPEAL_COUNT.labels(style=style).inc()


def record_search(search_type: str):
    """Record a property search metric."""
    PROPERTY_SEARCH_COUNT.labels(search_type=search_type).inc()


def record_error(error_type: str, endpoint: str):
    """Record an error metric."""
    ERROR_COUNT.labels(error_type=error_type, endpoint=endpoint).inc()


def capture_exception(exc: Exception, **context):
    """
    Capture exception in Sentry if configured.

    Falls back to logging if Sentry is not available.
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(exc)
    except ImportError:
        logger = get_logger("monitoring")
        logger.exception("Exception captured", exc_info=exc, **context)
