"""Provider timeout and retry logic with exponential backoff."""
from typing import Callable, Optional, TypeVar, Any, Coroutine
from datetime import datetime, timedelta
import time
import random
import logging
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryableError(Exception):
    """Exception that should trigger retry."""
    pass


class NonRetryableError(Exception):
    """Exception that should NOT trigger retry (e.g., 4xx errors)."""
    pass


def with_timeout_and_retry(
    timeout_seconds: float = 30.0,
    max_retries: int = 3,
    initial_backoff_seconds: float = 1.0,
    max_backoff_seconds: float = 10.0,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator for provider calls with timeout and exponential backoff retry.
    
    Args:
        timeout_seconds: Timeout per attempt
        max_retries: Maximum number of retries (total attempts = max_retries + 1)
        initial_backoff_seconds: Initial backoff delay
        max_backoff_seconds: Maximum backoff delay
        retryable_exceptions: Tuple of exceptions that should trigger retry
    
    Usage:
        @with_timeout_and_retry(timeout_seconds=30.0, max_retries=3)
        def call_provider_api(...):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Execute with timeout
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    if attempt > 0:
                        logger.info(
                            f"Provider call succeeded on attempt {attempt + 1}: "
                            f"{func.__name__}, duration={duration:.2f}s"
                        )
                    
                    return result
                
                except Exception as e:
                    last_exception = e
                    duration = time.time() - start_time if 'start_time' in locals() else 0
                    
                    # Check if exception is retryable
                    if not isinstance(e, retryable_exceptions):
                        logger.error(
                            f"Non-retryable error in {func.__name__}: {e}, "
                            f"attempt={attempt + 1}"
                        )
                        raise
                    
                    # Check if timeout exceeded
                    if duration >= timeout_seconds:
                        logger.warning(
                            f"Timeout in {func.__name__}: duration={duration:.2f}s > "
                            f"timeout={timeout_seconds}s, attempt={attempt + 1}"
                        )
                    
                    # Don't retry on last attempt
                    if attempt >= max_retries:
                        logger.error(
                            f"Max retries exceeded for {func.__name__}: {e}, "
                            f"attempts={attempt + 1}"
                        )
                        raise
                    
                    # Calculate exponential backoff with jitter
                    backoff = min(
                        initial_backoff_seconds * (2 ** attempt),
                        max_backoff_seconds
                    )
                    jitter = random.uniform(0, backoff * 0.1)  # 10% jitter
                    sleep_time = backoff + jitter
                    
                    logger.warning(
                        f"Retrying {func.__name__} after {sleep_time:.2f}s: {e}, "
                        f"attempt={attempt + 1}/{max_retries + 1}"
                    )
                    
                    time.sleep(sleep_time)
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            
            raise RuntimeError(f"Unexpected error in {func.__name__}")
        
        return wrapper
    return decorator


class ProviderTimeoutRetry:
    """
    Centralized timeout and retry logic for providers.
    
    Provides configurable timeouts and retries per provider.
    """
    
    # Default timeouts per provider (seconds)
    DEFAULT_TIMEOUTS = {
        "openai": 30.0,
        "huggingface": 60.0,  # Longer timeout for free tier
        "local": 120.0,  # Local models can be slower
        "ollama": 120.0,  # CPU inference can be slow (qwen2.5:3b ~10-15 tok/s)
        "groq": 15.0,  # Groq cloud is fast
        "serpapi": 10.0,
    }
    
    # Default retry counts per provider
    DEFAULT_RETRIES = {
        "openai": 3,
        "huggingface": 2,
        "local": 1,  # Local failures are usually permanent
        "ollama": 1,  # Local failures are usually permanent (circuit breaker handles recovery)
        "groq": 3,  # Cloud retries are cheap and fast
        "serpapi": 2,
    }
    
    def __init__(self):
        self.timeouts = self.DEFAULT_TIMEOUTS.copy()
        self.retries = self.DEFAULT_RETRIES.copy()
    
    def get_timeout(self, provider: str) -> float:
        """Get timeout for provider."""
        return self.timeouts.get(provider, 30.0)
    
    def get_max_retries(self, provider: str) -> int:
        """Get max retries for provider."""
        return self.retries.get(provider, 3)
    
    def execute_with_retry(
        self,
        provider: str,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> T:
        """
        Execute function with provider-specific timeout and retry.
        
        Args:
            provider: Provider name
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
        
        Returns:
            Function result
        
        Raises:
            Exception: If all retries fail
        """
        timeout = self.get_timeout(provider)
        max_retries = self.get_max_retries(provider)
        
        decorated_func = with_timeout_and_retry(
            timeout_seconds=timeout,
            max_retries=max_retries,
        )(func)
        
        return decorated_func(*args, **kwargs)
    
    def is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if error is retryable.
        
        Retryable: Timeout, 5xx errors, network errors
        Non-retryable: 4xx errors (client errors)
        """
        error_str = str(error).lower()
        
        # Check for non-retryable patterns
        non_retryable_patterns = [
            "400", "401", "403", "404",  # Client errors
            "invalid", "unauthorized", "forbidden", "not found",
            "bad request", "malformed",
        ]
        
        for pattern in non_retryable_patterns:
            if pattern in error_str:
                return False
        
        # Check for retryable patterns
        retryable_patterns = [
            "500", "502", "503", "504",  # Server errors
            "timeout", "connection", "network", "unavailable",
            "rate limit", "too many requests",  # Rate limits are retryable
        ]
        
        for pattern in retryable_patterns:
            if pattern in error_str:
                return True
        
        # Default: retryable (conservative)
        return True


# Global timeout/retry manager
_timeout_retry = ProviderTimeoutRetry()


def get_timeout_retry() -> ProviderTimeoutRetry:
    """Get global timeout/retry manager."""
    return _timeout_retry


def with_async_timeout_and_retry(
    timeout_seconds: float = 30.0,
    max_retries: int = 3,
    initial_backoff_seconds: float = 1.0,
    max_backoff_seconds: float = 10.0,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator for async provider calls with timeout and exponential backoff retry.
    
    Args:
        timeout_seconds: Timeout per attempt
        max_retries: Maximum number of retries
        initial_backoff_seconds: Initial backoff delay
        max_backoff_seconds: Maximum backoff delay
        retryable_exceptions: Tuple of exceptions that should trigger retry
    
    Usage:
        @with_async_timeout_and_retry(timeout_seconds=30.0, max_retries=3)
        async def call_provider_api(...):
            ...
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Execute with timeout
                    start_time = time.time()
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout_seconds,
                    )
                    duration = time.time() - start_time
                    
                    if attempt > 0:
                        logger.info(
                            f"Async provider call succeeded on attempt {attempt + 1}: "
                            f"{func.__name__}, duration={duration:.2f}s"
                        )
                    
                    return result
                
                except asyncio.TimeoutError:
                    duration = time.time() - start_time if 'start_time' in locals() else 0
                    last_exception = TimeoutError(
                        f"Timeout after {duration:.2f}s in {func.__name__}"
                    )
                    
                    if attempt >= max_retries:
                        logger.error(
                            f"Max retries exceeded for {func.__name__}: timeout, "
                            f"attempts={attempt + 1}"
                        )
                        raise last_exception
                    
                    backoff = min(
                        initial_backoff_seconds * (2 ** attempt),
                        max_backoff_seconds
                    )
                    jitter = random.uniform(0, backoff * 0.1)
                    sleep_time = backoff + jitter
                    
                    logger.warning(
                        f"Retrying {func.__name__} after {sleep_time:.2f}s: timeout, "
                        f"attempt={attempt + 1}/{max_retries + 1}"
                    )
                    
                    await asyncio.sleep(sleep_time)
                
                except Exception as e:
                    duration = time.time() - start_time if 'start_time' in locals() else 0
                    last_exception = e
                    
                    if not isinstance(e, retryable_exceptions):
                        logger.error(
                            f"Non-retryable error in {func.__name__}: {e}, "
                            f"attempt={attempt + 1}"
                        )
                        raise
                    
                    if attempt >= max_retries:
                        logger.error(
                            f"Max retries exceeded for {func.__name__}: {e}, "
                            f"attempts={attempt + 1}"
                        )
                        raise
                    
                    backoff = min(
                        initial_backoff_seconds * (2 ** attempt),
                        max_backoff_seconds
                    )
                    jitter = random.uniform(0, backoff * 0.1)
                    sleep_time = backoff + jitter
                    
                    logger.warning(
                        f"Retrying {func.__name__} after {sleep_time:.2f}s: {e}, "
                        f"attempt={attempt + 1}/{max_retries + 1}"
                    )
                    
                    await asyncio.sleep(sleep_time)
            
            if last_exception:
                raise last_exception
            
            raise RuntimeError(f"Unexpected error in {func.__name__}")
        
        return wrapper
    return decorator


class AsyncProviderTimeoutRetry:
    """Async version of ProviderTimeoutRetry."""
    
    DEFAULT_TIMEOUTS = ProviderTimeoutRetry.DEFAULT_TIMEOUTS.copy()
    DEFAULT_RETRIES = ProviderTimeoutRetry.DEFAULT_RETRIES.copy()
    
    def __init__(self):
        self.timeouts = self.DEFAULT_TIMEOUTS.copy()
        self.retries = self.DEFAULT_RETRIES.copy()
    
    def get_timeout(self, provider: str) -> float:
        """Get timeout for provider."""
        return self.timeouts.get(provider, 30.0)
    
    def get_max_retries(self, provider: str) -> int:
        """Get max retries for provider."""
        return self.retries.get(provider, 3)
    
    async def execute_with_retry(
        self,
        provider: str,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args,
        **kwargs,
    ) -> T:
        """Execute async function with provider-specific timeout and retry."""
        timeout = self.get_timeout(provider)
        max_retries = self.get_max_retries(provider)
        
        decorated_func = with_async_timeout_and_retry(
            timeout_seconds=timeout,
            max_retries=max_retries,
        )(func)
        
        return await decorated_func(*args, **kwargs)


# Global async timeout/retry manager
_async_timeout_retry = AsyncProviderTimeoutRetry()


def get_async_timeout_retry() -> AsyncProviderTimeoutRetry:
    """Get global async timeout/retry manager."""
    return _async_timeout_retry
