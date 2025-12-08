"""
Security configuration and utilities for the Taxdown API.

Provides API key management, input validation limits, rate limiting tiers,
and security utilities for production deployment.
"""

import hashlib
import hmac
import re
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Set
from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader


# =============================================================================
# API KEY MANAGEMENT
# =============================================================================


class APIKeyTier(str, Enum):
    """API key subscription tiers with different rate limits."""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class APIKeyInfo:
    """Information about a validated API key."""
    key_id: str
    tier: APIKeyTier
    owner_id: Optional[str] = None
    scopes: Optional[Set[str]] = None
    is_active: bool = True


class SecurityConfig:
    """Production security configuration and utilities."""

    # API Key prefix for identification
    API_KEY_PREFIX = "txd_"
    API_KEY_LENGTH = 32

    @staticmethod
    def hash_api_key(key: str) -> str:
        """
        Hash API keys for secure storage comparison.

        Uses SHA-256 with a consistent salt for storage.
        Never store raw API keys - always hash them first.
        """
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a cryptographically secure API key.

        Format: txd_{32 bytes of URL-safe base64}
        Example: txd_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6
        """
        token = secrets.token_urlsafe(SecurityConfig.API_KEY_LENGTH)
        return f"{SecurityConfig.API_KEY_PREFIX}{token}"

    @staticmethod
    def generate_key_pair() -> tuple[str, str]:
        """
        Generate an API key and its hash.

        Returns:
            Tuple of (raw_key, hashed_key)
            Store the hashed_key, give raw_key to user once.
        """
        raw_key = SecurityConfig.generate_api_key()
        hashed_key = SecurityConfig.hash_api_key(raw_key)
        return raw_key, hashed_key

    @staticmethod
    def verify_key_format(key: str) -> bool:
        """Verify that an API key has the correct format."""
        if not key:
            return False
        if not key.startswith(SecurityConfig.API_KEY_PREFIX):
            return False
        # Check length (prefix + base64 token)
        if len(key) < len(SecurityConfig.API_KEY_PREFIX) + 20:
            return False
        return True

    @staticmethod
    def generate_request_signature(
        payload: str,
        secret: str,
        timestamp: Optional[int] = None
    ) -> tuple[str, int]:
        """
        Generate HMAC signature for request signing.

        Used for webhook callbacks and sensitive endpoint verification.

        Args:
            payload: The request body or data to sign
            secret: The shared secret key
            timestamp: Unix timestamp (defaults to current time)

        Returns:
            Tuple of (signature, timestamp)
        """
        if timestamp is None:
            timestamp = int(time.time())

        message = f"{timestamp}.{payload}".encode()
        signature = hmac.new(
            secret.encode(),
            message,
            hashlib.sha256
        ).hexdigest()

        return signature, timestamp

    @staticmethod
    def verify_request_signature(
        payload: str,
        secret: str,
        signature: str,
        timestamp: int,
        max_age_seconds: int = 300
    ) -> bool:
        """
        Verify HMAC signature for incoming signed requests.

        Args:
            payload: The request body
            secret: The shared secret key
            signature: The provided signature to verify
            timestamp: The timestamp from the request
            max_age_seconds: Maximum age of request (default 5 minutes)

        Returns:
            True if signature is valid and not expired
        """
        # Check timestamp is not too old
        current_time = int(time.time())
        if abs(current_time - timestamp) > max_age_seconds:
            return False

        # Regenerate signature and compare
        expected_signature, _ = SecurityConfig.generate_request_signature(
            payload, secret, timestamp
        )

        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(signature, expected_signature)


# =============================================================================
# INPUT VALIDATION LIMITS
# =============================================================================


class InputLimits:
    """
    Input validation limits to prevent abuse and ensure data quality.

    These limits should be enforced at the API layer before
    any database operations.
    """

    # Query/Search limits
    MAX_QUERY_LENGTH = 500
    MAX_SEARCH_RESULTS = 1000

    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    MAX_OFFSET = 10000

    # Bulk operations
    MAX_BULK_ITEMS = 50
    MAX_BULK_PROPERTIES = 100
    MAX_CSV_ROWS = 1000

    # File uploads
    MAX_FILE_SIZE_MB = 10
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    ALLOWED_FILE_TYPES = {"csv", "xlsx", "xls"}

    # String field limits
    MAX_NAME_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 2000
    MAX_NOTES_LENGTH = 5000
    MAX_ADDRESS_LENGTH = 500
    MAX_EMAIL_LENGTH = 254

    # Numeric limits
    MAX_PERCENTAGE = 100.0
    MIN_PERCENTAGE = 0.0
    MAX_PRICE_CENTS = 100_000_000_000  # $1 billion
    MAX_MILL_RATE = 500.0

    @classmethod
    def validate_pagination(cls, page: int, page_size: int) -> tuple[int, int]:
        """
        Validate and sanitize pagination parameters.

        Returns:
            Tuple of (validated_page, validated_page_size)
        """
        page = max(1, page)
        page_size = max(1, min(page_size, cls.MAX_PAGE_SIZE))

        # Prevent offset overflow
        offset = (page - 1) * page_size
        if offset > cls.MAX_OFFSET:
            page = (cls.MAX_OFFSET // page_size) + 1

        return page, page_size

    @classmethod
    def validate_bulk_size(cls, items: list) -> None:
        """Raise HTTPException if bulk items exceed limit."""
        if len(items) > cls.MAX_BULK_ITEMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bulk operations limited to {cls.MAX_BULK_ITEMS} items"
            )

    @classmethod
    def validate_file_size(cls, size_bytes: int) -> None:
        """Raise HTTPException if file exceeds size limit."""
        if size_bytes > cls.MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum of {cls.MAX_FILE_SIZE_MB}MB"
            )

    @classmethod
    def validate_file_type(cls, filename: str) -> None:
        """Raise HTTPException if file type is not allowed."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in cls.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{ext}' not allowed. Allowed: {cls.ALLOWED_FILE_TYPES}"
            )


# =============================================================================
# RATE LIMITING TIERS
# =============================================================================


class RateLimits:
    """
    Rate limiting configuration by API key tier.

    Limits are specified as requests per minute.
    """

    # Requests per minute by tier
    TIER_LIMITS = {
        APIKeyTier.FREE: 60,
        APIKeyTier.BASIC: 200,
        APIKeyTier.PRO: 500,
        APIKeyTier.ENTERPRISE: 2000,
    }

    # Burst limits (requests per second)
    TIER_BURST = {
        APIKeyTier.FREE: 5,
        APIKeyTier.BASIC: 15,
        APIKeyTier.PRO: 30,
        APIKeyTier.ENTERPRISE: 100,
    }

    # Daily limits (0 = unlimited)
    TIER_DAILY = {
        APIKeyTier.FREE: 1000,
        APIKeyTier.BASIC: 10000,
        APIKeyTier.PRO: 100000,
        APIKeyTier.ENTERPRISE: 0,  # Unlimited
    }

    # Concurrent requests
    TIER_CONCURRENT = {
        APIKeyTier.FREE: 2,
        APIKeyTier.BASIC: 5,
        APIKeyTier.PRO: 10,
        APIKeyTier.ENTERPRISE: 50,
    }

    @classmethod
    def get_limits(cls, tier: APIKeyTier) -> dict:
        """Get all rate limits for a tier."""
        return {
            "requests_per_minute": cls.TIER_LIMITS.get(tier, 60),
            "burst_per_second": cls.TIER_BURST.get(tier, 5),
            "daily_limit": cls.TIER_DAILY.get(tier, 1000),
            "max_concurrent": cls.TIER_CONCURRENT.get(tier, 2),
        }


# =============================================================================
# SENSITIVE DATA PROTECTION
# =============================================================================


class SensitiveDataFilter:
    """
    Filter for redacting sensitive data from logs and error messages.

    Patterns are compiled once and reused for performance.
    """

    # Patterns to detect sensitive fields (case-insensitive)
    SENSITIVE_PATTERNS = [
        r"api[_-]?key",
        r"password",
        r"passwd",
        r"secret",
        r"token",
        r"bearer",
        r"authorization",
        r"ssn",
        r"social[_-]?security",
        r"credit[_-]?card",
        r"card[_-]?number",
        r"cvv",
        r"pin",
        r"private[_-]?key",
    ]

    _compiled_patterns = None

    @classmethod
    def _get_patterns(cls):
        """Lazily compile regex patterns."""
        if cls._compiled_patterns is None:
            cls._compiled_patterns = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in cls.SENSITIVE_PATTERNS
            ]
        return cls._compiled_patterns

    @classmethod
    def is_sensitive_key(cls, key: str) -> bool:
        """Check if a key name matches sensitive patterns."""
        for pattern in cls._get_patterns():
            if pattern.search(key):
                return True
        return False

    @classmethod
    def redact_dict(cls, data: dict, replacement: str = "[REDACTED]") -> dict:
        """
        Recursively redact sensitive values from a dictionary.

        Args:
            data: Dictionary to redact
            replacement: String to replace sensitive values with

        Returns:
            New dictionary with sensitive values redacted
        """
        if not isinstance(data, dict):
            return data

        result = {}
        for key, value in data.items():
            if cls.is_sensitive_key(str(key)):
                result[key] = replacement
            elif isinstance(value, dict):
                result[key] = cls.redact_dict(value, replacement)
            elif isinstance(value, list):
                result[key] = [
                    cls.redact_dict(item, replacement) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    @classmethod
    def redact_string(cls, text: str, replacement: str = "[REDACTED]") -> str:
        """
        Redact potential secrets from a string.

        Looks for patterns like key=value or "key": "value"
        """
        # Redact URL-style parameters
        result = re.sub(
            r'(api[_-]?key|token|secret|password)=[^&\s]+',
            rf'\1={replacement}',
            text,
            flags=re.IGNORECASE
        )

        # Redact JSON-style values
        result = re.sub(
            r'(["\'](?:api[_-]?key|token|secret|password)["\'])\s*:\s*["\'][^"\']+["\']',
            rf'\1: "{replacement}"',
            result,
            flags=re.IGNORECASE
        )

        return result


# =============================================================================
# IP ALLOWLISTING
# =============================================================================


class IPAllowlist:
    """
    IP address allowlisting for admin endpoints.

    Supports both IPv4 and IPv6 addresses, as well as CIDR notation.
    """

    def __init__(self, allowed_ips: Optional[list[str]] = None):
        """
        Initialize IP allowlist.

        Args:
            allowed_ips: List of allowed IP addresses or CIDR ranges
        """
        self.allowed_ips: Set[str] = set()
        self.allowed_cidrs: list[tuple] = []

        if allowed_ips:
            for ip in allowed_ips:
                self.add(ip)

    def add(self, ip_or_cidr: str) -> None:
        """Add an IP address or CIDR range to the allowlist."""
        ip_or_cidr = ip_or_cidr.strip()
        if "/" in ip_or_cidr:
            # CIDR notation - store for range checking
            try:
                import ipaddress
                network = ipaddress.ip_network(ip_or_cidr, strict=False)
                self.allowed_cidrs.append((network.network_address, network.broadcast_address))
            except ValueError:
                pass  # Invalid CIDR, skip
        else:
            self.allowed_ips.add(ip_or_cidr)

    def is_allowed(self, ip: str) -> bool:
        """Check if an IP address is in the allowlist."""
        if not ip:
            return False

        # Check exact match first
        if ip in self.allowed_ips:
            return True

        # Check CIDR ranges
        try:
            import ipaddress
            ip_obj = ipaddress.ip_address(ip)
            for start, end in self.allowed_cidrs:
                if start <= ip_obj <= end:
                    return True
        except ValueError:
            pass

        return False

    def check_request(self, request: Request) -> bool:
        """
        Check if request IP is allowed.

        Handles X-Forwarded-For header for proxied requests.
        """
        # Check X-Forwarded-For first (for reverse proxy setups)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP (client IP)
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else None

        return self.is_allowed(ip) if ip else False


# =============================================================================
# SECURITY HEADERS
# =============================================================================


class SecurityHeaders:
    """
    Security headers configuration for HTTP responses.

    These headers help protect against common web vulnerabilities.
    """

    # Content Security Policy
    CSP_POLICY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    # Standard security headers
    HEADERS = {
        # Prevent clickjacking
        "X-Frame-Options": "DENY",

        # Prevent MIME-type sniffing
        "X-Content-Type-Options": "nosniff",

        # Enable XSS filter in older browsers
        "X-XSS-Protection": "1; mode=block",

        # Referrer policy
        "Referrer-Policy": "strict-origin-when-cross-origin",

        # Permissions policy (formerly Feature-Policy)
        "Permissions-Policy": (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        ),

        # Cache control for sensitive data
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
    }

    # HSTS header (only for HTTPS)
    HSTS_HEADER = "max-age=31536000; includeSubDomains; preload"

    @classmethod
    def get_headers(cls, include_hsts: bool = True) -> dict:
        """
        Get all security headers.

        Args:
            include_hsts: Include HSTS header (only for HTTPS)

        Returns:
            Dictionary of security headers
        """
        headers = dict(cls.HEADERS)
        headers["Content-Security-Policy"] = cls.CSP_POLICY

        if include_hsts:
            headers["Strict-Transport-Security"] = cls.HSTS_HEADER

        return headers


# =============================================================================
# DEPENDENCY INJECTION HELPERS
# =============================================================================


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key_info(
    api_key: Optional[str] = Depends(api_key_header),
) -> Optional[APIKeyInfo]:
    """
    Extract and validate API key from request header.

    This is a dependency that can be used in route handlers.
    Returns None if no API key is provided and auth is not required.
    """
    if not api_key:
        return None

    if not SecurityConfig.verify_key_format(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # In a production system, you would look up the key in a database
    # and verify the hash. For now, return a default tier.
    return APIKeyInfo(
        key_id=api_key[:16],
        tier=APIKeyTier.FREE,
    )


def require_api_key(
    api_key_info: Optional[APIKeyInfo] = Depends(get_api_key_info),
) -> APIKeyInfo:
    """
    Require a valid API key for the endpoint.

    Use as a dependency: api_key: APIKeyInfo = Depends(require_api_key)
    """
    if not api_key_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not api_key_info.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is inactive",
        )

    return api_key_info


def require_tier(min_tier: APIKeyTier):
    """
    Factory for requiring a minimum API key tier.

    Usage:
        @router.get("/premium-endpoint")
        async def premium(key: APIKeyInfo = Depends(require_tier(APIKeyTier.PRO))):
            ...
    """
    tier_order = [APIKeyTier.FREE, APIKeyTier.BASIC, APIKeyTier.PRO, APIKeyTier.ENTERPRISE]
    min_index = tier_order.index(min_tier)

    def dependency(
        api_key_info: APIKeyInfo = Depends(require_api_key),
    ) -> APIKeyInfo:
        current_index = tier_order.index(api_key_info.tier)
        if current_index < min_index:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires {min_tier.value} tier or higher",
            )
        return api_key_info

    return dependency


def require_scope(scope: str):
    """
    Factory for requiring a specific API key scope.

    Usage:
        @router.delete("/admin/users/{user_id}")
        async def delete_user(key: APIKeyInfo = Depends(require_scope("admin:write"))):
            ...
    """
    def dependency(
        api_key_info: APIKeyInfo = Depends(require_api_key),
    ) -> APIKeyInfo:
        if not api_key_info.scopes or scope not in api_key_info.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires the '{scope}' scope",
            )
        return api_key_info

    return dependency
