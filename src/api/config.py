from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class APISettings(BaseSettings):
    # Application
    app_name: str = "Taxdown API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Monitoring - Sentry
    sentry_dsn: Optional[str] = None
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.1

    # Monitoring - Logging
    log_level: str = "INFO"
    log_json: bool = True  # Use JSON logs in production

    # Monitoring - Redis (for caching/rate limiting)
    redis_url: Optional[str] = None
    cache_enabled: bool = True  # Master switch for caching

    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://taxdown.vercel.app",
        "https://taxdown-nu.vercel.app",
        "https://www.taxdown.com",
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 40

    # Rate Limiting
    rate_limit_per_minute: int = 100
    rate_limit_burst: int = 20

    # API Keys (simple auth for MVP)
    api_keys: List[str] = []  # Loaded from env
    require_api_key: bool = False  # Disable for development

    # Feature Flags
    enable_claude_api: bool = False
    enable_bulk_operations: bool = True
    max_bulk_properties: int = 100

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100

    # ==========================================================================
    # SECURITY SETTINGS
    # ==========================================================================

    # HTTPS/HSTS
    enable_hsts: bool = True  # Enable Strict-Transport-Security header
    hsts_max_age: int = 31536000  # 1 year in seconds

    # Secure Headers
    enable_secure_headers: bool = True

    # Audit Logging
    enable_audit_logging: bool = True
    audit_log_reads: bool = False  # Log GET requests (can be noisy)
    audit_log_to_database: bool = False  # Persist audit logs to DB

    # IP Allowlisting (for admin endpoints)
    admin_allowed_ips: List[str] = []  # Empty = allow all
    enable_ip_allowlist: bool = False

    # Request Signing (for webhooks and sensitive endpoints)
    webhook_secret: Optional[str] = None
    request_signature_max_age: int = 300  # 5 minutes

    # API Key Rotation
    api_key_rotation_days: int = 90  # Recommended key rotation period
    warn_key_expiry_days: int = 14  # Warn before expiration

    # Input Validation
    max_request_size_mb: int = 10
    max_query_length: int = 500
    max_bulk_items: int = 50

    # Session/Token Settings
    token_expiry_hours: int = 24
    refresh_token_expiry_days: int = 30

    class Config:
        env_file = ".env"
        env_prefix = "TAXDOWN_"
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


@lru_cache()
def get_settings() -> APISettings:
    return APISettings()
