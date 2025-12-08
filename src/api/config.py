from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class APISettings(BaseSettings):
    # Application
    app_name: str = "Taxdown API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
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

    class Config:
        env_file = ".env"
        env_prefix = "TAXDOWN_"
        extra = "ignore"


@lru_cache()
def get_settings() -> APISettings:
    return APISettings()
