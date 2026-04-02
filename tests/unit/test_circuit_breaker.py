"""Tests for the circuit breaker pattern."""

import time
from unittest.mock import patch

import pytest

from src.integrations.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitOpenError,
    CircuitState,
)


class TestCircuitBreakerStates:
    """Test state transitions: CLOSED → OPEN → HALF_OPEN → CLOSED."""

    def test_starts_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_stays_closed_under_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_opens_at_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_open_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.allow_request() is True

    def test_half_open_success_closes_circuit(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        time.sleep(0.15)

        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens_circuit(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        time.sleep(0.15)

        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False


class TestCircuitBreakerEdgeCases:
    """Edge cases and advanced behavior."""

    def test_manual_reset(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.allow_request() is True

    def test_time_until_retry_when_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.time_until_retry() == 0.0

    def test_time_until_retry_when_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60.0)
        cb.record_failure()
        remaining = cb.time_until_retry()
        assert 59.0 < remaining <= 60.0

    def test_get_stats(self):
        cb = CircuitBreaker("openai", failure_threshold=5, recovery_timeout=30.0)
        cb.record_failure()
        stats = cb.get_stats()
        assert stats["provider"] == "openai"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 1
        assert stats["failure_threshold"] == 5

    def test_success_threshold_multiple(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05, success_threshold=2)
        cb.record_failure()
        time.sleep(0.1)

        # Confirm HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN

        # First success: still HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN

        # Second success: closes
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_repr(self):
        cb = CircuitBreaker("openai", failure_threshold=5)
        r = repr(cb)
        assert "openai" in r
        assert "closed" in r


class TestCircuitBreakerRegistry:
    """Test the registry that manages multiple breakers."""

    def test_creates_breaker_on_first_access(self):
        registry = CircuitBreakerRegistry()
        cb = registry.get("openai")
        assert isinstance(cb, CircuitBreaker)
        assert cb.provider == "openai"

    def test_returns_same_breaker_for_same_provider(self):
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("openai")
        cb2 = registry.get("openai")
        assert cb1 is cb2

    def test_separate_breakers_per_provider(self):
        registry = CircuitBreakerRegistry()
        cb_openai = registry.get("openai")
        cb_anthropic = registry.get("anthropic")
        assert cb_openai is not cb_anthropic

        cb_openai.record_failure()
        assert cb_anthropic.failure_count == 0

    def test_get_all_stats(self):
        registry = CircuitBreakerRegistry()
        registry.get("openai").record_failure()
        registry.get("anthropic")

        stats = registry.get_all_stats()
        assert len(stats) == 2
        providers = {s["provider"] for s in stats}
        assert providers == {"openai", "anthropic"}

    def test_reset_all(self):
        registry = CircuitBreakerRegistry(failure_threshold=1)
        registry.get("openai").record_failure()
        registry.get("anthropic").record_failure()

        assert registry.get("openai").state == CircuitState.OPEN
        assert registry.get("anthropic").state == CircuitState.OPEN

        registry.reset_all()
        assert registry.get("openai").state == CircuitState.CLOSED
        assert registry.get("anthropic").state == CircuitState.CLOSED

    def test_custom_defaults(self):
        registry = CircuitBreakerRegistry(failure_threshold=10, recovery_timeout=120.0)
        cb = registry.get("test")
        assert cb.failure_threshold == 10
        assert cb.recovery_timeout == 120.0

    def test_repr(self):
        registry = CircuitBreakerRegistry()
        registry.get("openai")
        r = repr(registry)
        assert "openai" in r


class TestCircuitOpenError:
    """Test the CircuitOpenError exception."""

    def test_error_message(self):
        err = CircuitOpenError("openai", retry_after=30.0)
        assert "openai" in str(err)
        assert "30" in str(err)
        assert err.provider == "openai"
        assert err.retry_after == 30.0
