"""
Redis Caching Implementation for Taxdown API.

Provides a CacheManager class and decorator for caching API responses.
Gracefully handles missing Redis connection by disabling caching.
"""

import json
import hashlib
import logging
from typing import Optional, Any, Callable, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

# Type variable for generic return types
T = TypeVar('T')


class CacheManager:
    """
    Redis-based cache manager with graceful fallback.

    If Redis is unavailable, caching is silently disabled and all
    operations become no-ops.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the cache manager.

        Args:
            redis_url: Redis connection URL. If None, caching is disabled.
        """
        self.enabled = False
        self.redis = None

        if redis_url:
            try:
                import redis as redis_lib
                self.redis = redis_lib.from_url(
                    redis_url,
                    decode_responses=True,  # Return strings instead of bytes
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                # Test connection
                self.redis.ping()
                self.enabled = True
                logger.info("Redis cache connected successfully")
            except ImportError:
                logger.warning("Redis library not installed. Caching disabled.")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Caching disabled.")

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate a cache key from prefix and arguments.

        Args:
            prefix: Key prefix (e.g., 'property_detail')
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key

        Returns:
            Cache key string like 'taxdown:property_detail:abc123def456'
        """
        # Create deterministic key from arguments
        key_data = json.dumps(
            {"args": args, "kwargs": kwargs},
            sort_keys=True,
            default=str  # Handle UUIDs and other non-serializable types
        )
        hash_value = hashlib.md5(key_data.encode()).hexdigest()[:12]
        return f"taxdown:{prefix}:{hash_value}"

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/disabled
        """
        if not self.enabled:
            return None

        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")

        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default 5 minutes)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            serialized = json.dumps(value, default=str)
            self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False otherwise
        """
        if not self.enabled:
            return False

        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., 'property_*' to delete all property caches)

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            deleted = 0
            full_pattern = f"taxdown:{pattern}:*"
            for key in self.redis.scan_iter(full_pattern):
                self.redis.delete(key)
                deleted += 1
            return deleted
        except Exception as e:
            logger.warning(f"Cache delete_pattern error for {pattern}: {e}")
            return 0

    def invalidate_property(self, property_id: str):
        """
        Invalidate all caches related to a specific property.

        Call this when a property is updated or analysis changes.

        Args:
            property_id: Property ID to invalidate
        """
        # Delete property detail cache
        self.delete_pattern(f"property_detail:*{property_id[:8]}*")
        # Delete analysis cache
        self.delete_pattern(f"analysis:*{property_id[:8]}*")
        # Delete comparables cache
        self.delete_pattern(f"comparables:*{property_id[:8]}*")

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats or empty dict if disabled
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            info = self.redis.info("stats")
            return {
                "enabled": True,
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "connected_clients": self.redis.info("clients").get("connected_clients", 0),
            }
        except Exception as e:
            logger.warning(f"Cache stats error: {e}")
            return {"enabled": True, "error": str(e)}


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    Get the global cache manager instance.

    Initializes with REDIS_URL from settings if not already created.
    """
    global _cache_manager
    if _cache_manager is None:
        from src.api.config import get_settings
        settings = get_settings()
        redis_url = getattr(settings, 'redis_url', None)
        _cache_manager = CacheManager(redis_url)
    return _cache_manager


def init_cache(redis_url: Optional[str] = None) -> CacheManager:
    """
    Initialize or reinitialize the cache manager.

    Args:
        redis_url: Redis connection URL

    Returns:
        CacheManager instance
    """
    global _cache_manager
    _cache_manager = CacheManager(redis_url)
    return _cache_manager


# TTL constants based on data volatility
class CacheTTL:
    """Cache TTL values in seconds."""
    PROPERTY_DETAIL = 600      # 10 min - property data changes infrequently
    SEARCH_RESULTS = 300       # 5 min - balance freshness/performance
    ANALYSIS_RESULTS = 1800    # 30 min - computationally expensive
    COMPARABLES = 900          # 15 min - semi-static
    DASHBOARD_METRICS = 300    # 5 min - should feel current
    STATIC_LOOKUPS = 3600      # 1 hour - cities, property types, etc.
    AUTOCOMPLETE = 600         # 10 min - address suggestions


def cached(prefix: str, ttl: int = 300):
    """
    Decorator for caching async function results.

    Args:
        prefix: Cache key prefix (e.g., 'property_detail')
        ttl: Time to live in seconds

    Example:
        @cached("property_detail", ttl=CacheTTL.PROPERTY_DETAIL)
        async def get_property_detail(property_id: str):
            # ... database query
            return result
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            cache = get_cache_manager()

            # Skip 'self' or 'cls' for methods, and skip non-hashable args
            cache_args = args[1:] if args and hasattr(args[0], '__class__') else args

            # Generate cache key
            key = cache._make_key(prefix, *cache_args, **kwargs)

            # Try to get from cache
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {key}")
                return cached_value

            # Cache miss - execute function
            logger.debug(f"Cache miss: {key}")
            result = await func(*args, **kwargs)

            # Cache the result (only if not None)
            if result is not None:
                cache.set(key, result, ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            cache = get_cache_manager()

            cache_args = args[1:] if args and hasattr(args[0], '__class__') else args
            key = cache._make_key(prefix, *cache_args, **kwargs)

            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {key}")
                return cached_value

            logger.debug(f"Cache miss: {key}")
            result = func(*args, **kwargs)

            if result is not None:
                cache.set(key, result, ttl)

            return result

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key for manual caching.

    Args:
        *args: Values to include in key
        **kwargs: Named values to include in key

    Returns:
        Hash string suitable for use as cache key suffix
    """
    key_data = json.dumps(
        {"args": args, "kwargs": kwargs},
        sort_keys=True,
        default=str
    )
    return hashlib.md5(key_data.encode()).hexdigest()[:12]
