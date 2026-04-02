"""Circuit breaker for provider failures - prevents cascading failures."""

from typing import Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker for providers.

    Prevents cascading failures by stopping requests to failing providers.
    Opens circuit after threshold failures, tests recovery periodically.
    """

    def __init__(
        self,
        provider: str,
        failure_threshold: int = 5,
        failure_window_seconds: int = 60,
        recovery_timeout_seconds: int = 30,
        success_threshold: int = 2,
    ):
        self.provider = provider
        self.failure_threshold = failure_threshold
        self.failure_window_seconds = failure_window_seconds
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failures: list[datetime] = []  # Timestamps of recent failures
        self.successes: int = 0  # Success count in half-open state
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None

    def call(self, func, *args, **kwargs):
        """
        Execute function call with circuit breaker protection.

        Returns function result or raises exception.
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (
                self.opened_at
                and (datetime.utcnow() - self.opened_at).total_seconds()
                >= self.recovery_timeout_seconds
            ):
                # Transition to half-open
                self.state = CircuitState.HALF_OPEN
                self.successes = 0
                logger.info(f"Circuit breaker for {self.provider} transitioning to HALF_OPEN")
            else:
                # Still in open state, reject request
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN for provider {self.provider}. "
                    f"Last failure: {self.last_failure_time}"
                )

        # Attempt call
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise

    def _record_success(self):
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.success_threshold:
                # Circuit recovered, close it
                self.state = CircuitState.CLOSED
                self.failures.clear()
                self.successes = 0
                logger.info(f"Circuit breaker for {self.provider} recovered, closing circuit")
        else:
            # In closed state, clear old failures on success
            self._clean_old_failures()

    def _record_failure(self):
        """Record failed call."""
        now = datetime.utcnow()
        self.failures.append(now)
        self.last_failure_time = now

        # Clean old failures outside window
        self._clean_old_failures()

        # Count failures in window
        recent_failures = [
            f for f in self.failures if (now - f).total_seconds() <= self.failure_window_seconds
        ]

        if len(recent_failures) >= self.failure_threshold:
            # Open circuit
            if self.state != CircuitState.OPEN:
                self.state = CircuitState.OPEN
                self.opened_at = now
                logger.warning(
                    f"Circuit breaker for {self.provider} OPENED: "
                    f"{len(recent_failures)} failures in {self.failure_window_seconds}s"
                )

        # Reset successes if in half-open
        if self.state == CircuitState.HALF_OPEN:
            self.successes = 0
            self.state = CircuitState.OPEN
            self.opened_at = now

    def _clean_old_failures(self):
        """Remove failures outside the time window."""
        now = datetime.utcnow()
        self.failures = [
            f for f in self.failures if (now - f).total_seconds() <= self.failure_window_seconds
        ]

    def get_state(self) -> Dict:
        """Get current circuit breaker state."""
        return {
            "provider": self.provider,
            "state": self.state.value,
            "failure_count": len(self.failures),
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
        }

    def reset(self):
        """Manually reset circuit breaker (for testing/admin)."""
        self.state = CircuitState.CLOSED
        self.failures.clear()
        self.successes = 0
        self.opened_at = None
        self.last_failure_time = None
        logger.info(f"Circuit breaker for {self.provider} manually reset")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreakerManager:
    """Manage circuit breakers for all providers."""

    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, provider: str) -> CircuitBreaker:
        """Get or create circuit breaker for provider."""
        if provider not in self.breakers:
            self.breakers[provider] = CircuitBreaker(provider)
        return self.breakers[provider]

    def is_open(self, provider: str) -> bool:
        """Check if circuit breaker is open for provider."""
        breaker = self.get_breaker(provider)
        return breaker.state == CircuitState.OPEN

    def get_all_states(self) -> Dict[str, Dict]:
        """Get states of all circuit breakers."""
        return {provider: breaker.get_state() for provider, breaker in self.breakers.items()}


# Global circuit breaker manager
_circuit_breaker_manager = CircuitBreakerManager()


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager."""
    return _circuit_breaker_manager
