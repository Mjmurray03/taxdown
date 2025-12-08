"""Database configuration module."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# Load environment variables from .env file
load_dotenv()


def get_database_url(use_local: bool = False) -> str:
    """
    Get the database URL from environment variables.

    Args:
        use_local: If True, returns DATABASE_URL_LOCAL instead of DATABASE_URL

    Returns:
        Database connection URL string

    Raises:
        ValueError: If the required environment variable is not set
    """
    env_var = "DATABASE_URL_LOCAL" if use_local else "DATABASE_URL"
    url = os.getenv(env_var)

    if not url:
        raise ValueError(f"{env_var} environment variable is not set")

    return url


def get_engine(use_local: bool = False, **kwargs) -> Engine:
    """
    Create and return a SQLAlchemy engine.

    Args:
        use_local: If True, connects to local database
        **kwargs: Additional arguments passed to create_engine

    Returns:
        SQLAlchemy Engine instance
    """
    url = get_database_url(use_local=use_local)
    return create_engine(url, **kwargs)
