# src/api/resilience.py

from typing import TypeVar, Callable, Any
import asyncio
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open and service is unavailable."""
    pass


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(self, failure_threshold: int = 5, recovery_time: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        if self.state == "open":
            if self._should_attempt_recovery():
                self.state = "half-open"
            else:
                raise CircuitBreakerOpen("Service temporarily unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Async version of circuit breaker call."""
        if self.state == "open":
            if self._should_attempt_recovery():
                self.state = "half-open"
            else:
                raise CircuitBreakerOpen("Service temporarily unavailable")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failures = 0
        self.state = "closed"

    def _on_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker opened after {self.failures} failures"
            )

    def _should_attempt_recovery(self) -> bool:
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time > self.recovery_time

    def reset(self):
        """Manually reset the circuit breaker."""
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"


def with_fallback(fallback_value: Any):
    """Decorator to provide fallback value on failure."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Function {func.__name__} failed, using fallback", exc_info=True)
                return fallback_value
        return wrapper
    return decorator


def with_fallback_sync(fallback_value: Any):
    """Decorator to provide fallback value on failure (sync version)."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Function {func.__name__} failed, using fallback", exc_info=True)
                return fallback_value
        return wrapper
    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}, "
                            f"retrying in {current_delay:.1f}s: {e}"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff

            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator


def retry_sync(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """Retry decorator with exponential backoff (sync version)."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}, "
                            f"retrying in {current_delay:.1f}s: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff

            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator


class Timeout:
    """Context manager for async timeout."""

    def __init__(self, seconds: float):
        self.seconds = seconds

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def run(self, coro):
        """Run coroutine with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=self.seconds)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {self.seconds} seconds")
