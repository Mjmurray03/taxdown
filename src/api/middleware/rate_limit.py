from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
import asyncio
import time


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.

    For production, use Redis-based rate limiting.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 100,
        burst_limit: int = 20,
        exclude_paths: list = None
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]

        # Store: {client_key: [timestamp, ...]}
        self.request_counts: Dict[str, list] = defaultdict(list)
        self.lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Get client identifier (IP or API key)
        client_key = self._get_client_key(request)

        # Check rate limit
        is_allowed, retry_after = await self._check_rate_limit(client_key)

        if not is_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "status": "error",
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Too many requests. Retry after {retry_after} seconds.",
                        "retry_after": retry_after
                    }
                },
                headers={"Retry-After": str(retry_after)}
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = await self._get_remaining(client_key)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)

        return response

    def _get_client_key(self, request: Request) -> str:
        """Get unique client identifier."""
        # Prefer API key if present
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key[:16]}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    async def _check_rate_limit(self, client_key: str) -> Tuple[bool, int]:
        """Check if request is within rate limit."""
        async with self.lock:
            now = time.time()
            minute_ago = now - 60

            # Clean old entries
            self.request_counts[client_key] = [
                ts for ts in self.request_counts[client_key]
                if ts > minute_ago
            ]

            # Check limit
            current_count = len(self.request_counts[client_key])

            if current_count >= self.requests_per_minute:
                # Calculate retry after
                oldest = min(self.request_counts[client_key])
                retry_after = int(oldest + 60 - now) + 1
                return False, max(retry_after, 1)

            # Check burst (requests in last second)
            second_ago = now - 1
            recent_count = sum(1 for ts in self.request_counts[client_key] if ts > second_ago)

            if recent_count >= self.burst_limit:
                return False, 1

            # Allow request
            self.request_counts[client_key].append(now)
            return True, 0

    async def _get_remaining(self, client_key: str) -> int:
        """Get remaining requests in current window."""
        async with self.lock:
            now = time.time()
            minute_ago = now - 60

            current_count = sum(
                1 for ts in self.request_counts[client_key]
                if ts > minute_ago
            )

            return max(0, self.requests_per_minute - current_count)


class APIKeyRateLimiter:
    """
    Rate limiter with different limits per API key tier.
    """

    TIER_LIMITS = {
        "FREE": 60,
        "BASIC": 200,
        "PRO": 500,
        "ENTERPRISE": 2000
    }

    def __init__(self):
        self.request_counts: Dict[str, list] = defaultdict(list)

    def get_limit_for_tier(self, tier: str) -> int:
        return self.TIER_LIMITS.get(tier, 60)
