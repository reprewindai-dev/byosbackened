"""
Redis-backed circuit breaker for Ollama.

States:
  CLOSED   — Ollama healthy, all requests go through
  OPEN     — N consecutive failures; requests immediately routed to Groq
  HALF_OPEN — cooldown elapsed; next request probes Ollama to check recovery

Redis keys (per tenant):
  byos:cb:failures        — failure counter (INT)
  byos:cb:state           — "closed" | "open" | "half_open"
  byos:cb:opened_at       — unix timestamp when circuit opened
"""
import time
import logging
from enum import Enum
from typing import Optional

import redis as redis_lib
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_CB_FAILURES_KEY = "byos:cb:failures"
_CB_STATE_KEY = "byos:cb:state"
_CB_OPENED_AT_KEY = "byos:cb:opened_at"

_STATE_CLOSED = "closed"
_STATE_OPEN = "open"
_STATE_HALF_OPEN = "half_open"


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


def _redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)


def get_state() -> CircuitState:
    """Return the current circuit breaker state."""
    try:
        r = _redis()
        state = r.get(_CB_STATE_KEY) or _STATE_CLOSED

        if state == _STATE_OPEN:
            opened_at = float(r.get(_CB_OPENED_AT_KEY) or 0)
            if time.time() - opened_at >= settings.circuit_breaker_cooldown_seconds:
                r.set(_CB_STATE_KEY, _STATE_HALF_OPEN)
                logger.info("[CB] Circuit half-opened — probing Ollama")
                return CircuitState.HALF_OPEN

        return CircuitState(state)
    except Exception as e:
        logger.warning("[CB] Redis unavailable, assuming CLOSED: %s", e)
        return CircuitState.CLOSED


def record_success() -> None:
    """Call after a successful Ollama response. Resets the circuit."""
    try:
        r = _redis()
        pipe = r.pipeline()
        pipe.set(_CB_STATE_KEY, _STATE_CLOSED)
        pipe.set(_CB_FAILURES_KEY, 0)
        pipe.delete(_CB_OPENED_AT_KEY)
        pipe.execute()
        logger.debug("[CB] Circuit closed (success recorded)")
    except Exception as e:
        logger.warning("[CB] Could not record success: %s", e)


def record_failure() -> CircuitState:
    """
    Call after an Ollama failure. Increments counter; opens circuit
    if threshold is reached. Returns new state.
    """
    try:
        r = _redis()
        failures = r.incr(_CB_FAILURES_KEY)
        # Auto-expire failures counter after 5 minutes of inactivity
        r.expire(_CB_FAILURES_KEY, 300)

        if failures >= settings.circuit_breaker_failure_threshold:
            r.set(_CB_STATE_KEY, _STATE_OPEN)
            r.set(_CB_OPENED_AT_KEY, time.time())
            logger.warning(
                "[CB] Circuit OPENED after %d consecutive Ollama failures — routing to Groq",
                failures,
            )
            return CircuitState.OPEN

        logger.debug("[CB] Failure #%d (threshold=%d)", failures, settings.circuit_breaker_failure_threshold)
        return CircuitState.CLOSED
    except Exception as e:
        logger.warning("[CB] Could not record failure: %s", e)
        return CircuitState.CLOSED


def is_open() -> bool:
    """True when Ollama should NOT be called (circuit open)."""
    return get_state() == CircuitState.OPEN


def status_dict() -> dict:
    """Return circuit breaker state as dict for /status endpoint."""
    try:
        r = _redis()
        state = get_state()
        failures = int(r.get(_CB_FAILURES_KEY) or 0)
        opened_at = r.get(_CB_OPENED_AT_KEY)
        return {
            "state": state.value,
            "failures": failures,
            "threshold": settings.circuit_breaker_failure_threshold,
            "opened_at": float(opened_at) if opened_at else None,
        }
    except Exception:
        return {"state": "unknown", "failures": 0, "threshold": settings.circuit_breaker_failure_threshold}
