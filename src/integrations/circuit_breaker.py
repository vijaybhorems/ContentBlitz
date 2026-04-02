"""Circuit breaker pattern to prevent cascading API failures.

Implements a per-provider circuit breaker that tracks failures and
temporarily blocks requests to unhealthy providers, allowing the
system to fail fast and recover gracefully.

States:
    CLOSED   → Normal operation. Requests flow through. Failures are counted.
    OPEN     → Provider is unhealthy. Requests are immediately rejected.
                Transitions to HALF_OPEN after `recovery_timeout` seconds.
    HALF_OPEN → One probe request is allowed through.
                If it succeeds → CLOSED. If it fails → OPEN.

Usage:
    breaker = CircuitBreaker("openai", failure_threshold=3, recovery_timeout=30)

    if not breaker.allow_request():
        raise CircuitOpenError("openai")

    try:
        result = await call_openai(...)
        breaker.record_success()
    except Exception as e:
        breaker.record_failure()
        raise
"""

import time
from enum import Enum
from threading import Lock
from typing import Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Lifecycle states for a circuit breaker (normal, failing, probing)."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a request is rejected because the circuit is open."""

    def __init__(self, provider: str, retry_after: float):
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker OPEN for {provider}. "
            f"Retry after {retry_after:.0f}s."
        )


class CircuitBreaker:
    """Thread-safe circuit breaker for a single provider.

    Args:
        provider: Name of the external service (e.g. "openai", "tavily").
        failure_threshold: Number of consecutive failures before opening.
        recovery_timeout: Seconds to wait in OPEN state before probing.
        success_threshold: Successes needed in HALF_OPEN to close.
    """

    def __init__(
        self,
        provider: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 1,
    ):
        self.provider = provider
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None
        self._lock = Lock()

    # -- Public API --

    @property
    def state(self) -> CircuitState:
        """Current state, evaluated lazily (OPEN may transition to HALF_OPEN)."""
        with self._lock:
            self._evaluate_state()
            return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def allow_request(self) -> bool:
        """Check if a request should be allowed through.

        Returns:
            True if the request can proceed, False if it should be rejected.
        """
        with self._lock:
            self._evaluate_state()

            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.HALF_OPEN:
                # Allow exactly one probe request
                return True

            # OPEN — reject
            return False

    def record_success(self) -> None:
        """Record a successful request."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
            else:
                # Reset failure count on success in CLOSED state
                self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # Probe failed → back to OPEN
                self._transition_to(CircuitState.OPEN)

            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def reset(self) -> None:
        """Manually reset the breaker to CLOSED state."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)

    def time_until_retry(self) -> float:
        """Seconds remaining before the breaker transitions from OPEN to HALF_OPEN."""
        with self._lock:
            if self._state != CircuitState.OPEN or self._opened_at is None:
                return 0.0
            elapsed = time.monotonic() - self._opened_at
            remaining = self.recovery_timeout - elapsed
            return max(0.0, remaining)

    def get_stats(self) -> dict:
        """Return circuit breaker stats for observability."""
        return {
            "provider": self.provider,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "time_until_retry": round(self.time_until_retry(), 1),
        }

    # -- Internal helpers --

    def _evaluate_state(self) -> None:
        """Check if OPEN → HALF_OPEN transition is due."""
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(
                    "circuit_half_open",
                    provider=self.provider,
                    elapsed_s=round(elapsed, 1),
                )

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state with logging and counter resets."""
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.OPEN:
            self._opened_at = time.monotonic()
            self._success_count = 0
            logger.warning(
                "circuit_opened",
                provider=self.provider,
                failure_count=self._failure_count,
                recovery_timeout=self.recovery_timeout,
            )

        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            self._opened_at = None
            if old_state != CircuitState.CLOSED:
                logger.info(
                    "circuit_closed",
                    provider=self.provider,
                    previous_state=old_state.value,
                )

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(provider={self.provider!r}, state={self._state.value}, "
            f"failures={self._failure_count}/{self.failure_threshold})"
        )


class CircuitBreakerRegistry:
    """Registry of circuit breakers for all providers.

    Provides a central place to create, access, and monitor breakers.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._default_failure_threshold = failure_threshold
        self._default_recovery_timeout = recovery_timeout
        self._lock = Lock()

    def get(self, provider: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a provider."""
        with self._lock:
            if provider not in self._breakers:
                self._breakers[provider] = CircuitBreaker(
                    provider=provider,
                    failure_threshold=self._default_failure_threshold,
                    recovery_timeout=self._default_recovery_timeout,
                )
            return self._breakers[provider]

    def get_all_stats(self) -> list[dict]:
        """Return stats for all registered breakers."""
        return [b.get_stats() for b in self._breakers.values()]

    def reset_all(self) -> None:
        """Reset all breakers to CLOSED."""
        for b in self._breakers.values():
            b.reset()

    def __repr__(self) -> str:
        states = {name: b.state.value for name, b in self._breakers.items()}
        return f"CircuitBreakerRegistry({states})"
