"""
Redis-backed circuit breaker for Ollama.

States:
  CLOSED    - Ollama healthy, requests use the selected primary runtime.
  OPEN      - N scoped failures; matching requests route to approved fallback.
  HALF_OPEN - cooldown elapsed; next matching request probes Ollama recovery.

Redis keys are scoped by workspace/model so one failing runtime path does not
force unrelated tenants or models onto fallback.
"""
import logging
import re
import time
from enum import Enum
from typing import Optional

from core.config import get_settings
from core.redis_pool import get_redis

logger = logging.getLogger(__name__)
settings = get_settings()

_CB_FAILURES_KEY = "byos:cb:failures"
_CB_STATE_KEY = "byos:cb:state"
_CB_OPENED_AT_KEY = "byos:cb:opened_at"
_DEFAULT_SCOPE = "default"

_STATE_CLOSED = "closed"
_STATE_OPEN = "open"
_STATE_HALF_OPEN = "half_open"


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


def _redis():
    """Get Redis from shared connection pool."""
    return get_redis()


def _scope_token(scope: Optional[str]) -> str:
    token = (scope or _DEFAULT_SCOPE).strip() or _DEFAULT_SCOPE
    return re.sub(r"[^A-Za-z0-9_.:-]", "_", token)[:160]


def _scoped_key(base: str, scope: Optional[str]) -> str:
    token = _scope_token(scope)
    return base if token == _DEFAULT_SCOPE else f"{base}:{token}"


def get_state(scope: Optional[str] = None) -> CircuitState:
    """Return the current circuit breaker state."""
    state_key = _scoped_key(_CB_STATE_KEY, scope)
    opened_at_key = _scoped_key(_CB_OPENED_AT_KEY, scope)
    try:
        r = _redis()
        pipe = r.pipeline()
        pipe.get(state_key)
        pipe.get(opened_at_key)
        results = pipe.execute()

        state = results[0] or _STATE_CLOSED

        if state == _STATE_OPEN:
            opened_at = float(results[1] or 0)
            if time.time() - opened_at >= settings.circuit_breaker_cooldown_seconds:
                pipe = r.pipeline()
                pipe.set(state_key, _STATE_HALF_OPEN)
                pipe.execute()
                logger.info("[CB] Circuit half-opened - probing Ollama", extra={"scope": _scope_token(scope)})
                return CircuitState.HALF_OPEN

        return CircuitState(state)
    except Exception as exc:
        logger.warning("[CB] Redis unavailable, assuming CLOSED: %s", exc, extra={"scope": _scope_token(scope)})
        return CircuitState.CLOSED


def record_success(scope: Optional[str] = None) -> None:
    """Call after a successful Ollama response. Resets the scoped circuit."""
    failures_key = _scoped_key(_CB_FAILURES_KEY, scope)
    state_key = _scoped_key(_CB_STATE_KEY, scope)
    opened_at_key = _scoped_key(_CB_OPENED_AT_KEY, scope)
    try:
        r = _redis()
        pipe = r.pipeline()
        pipe.set(state_key, _STATE_CLOSED)
        pipe.set(failures_key, 0)
        pipe.delete(opened_at_key)
        pipe.execute()
        logger.debug("[CB] Circuit closed (success recorded)", extra={"scope": _scope_token(scope)})
    except Exception as exc:
        logger.warning("[CB] Could not record success: %s", exc, extra={"scope": _scope_token(scope)})


def record_failure(scope: Optional[str] = None) -> CircuitState:
    """
    Call after an Ollama failure. Increments the scoped counter and opens the
    scoped circuit if the threshold is reached. Returns the new state.
    """
    failures_key = _scoped_key(_CB_FAILURES_KEY, scope)
    state_key = _scoped_key(_CB_STATE_KEY, scope)
    opened_at_key = _scoped_key(_CB_OPENED_AT_KEY, scope)
    try:
        r = _redis()
        failures = r.incr(failures_key)
        r.expire(failures_key, 300)

        if failures >= settings.circuit_breaker_failure_threshold:
            r.set(state_key, _STATE_OPEN)
            r.set(opened_at_key, time.time())
            logger.warning(
                "[CB] Circuit OPENED after %d consecutive Ollama failures - routing to fallback",
                failures,
                extra={"scope": _scope_token(scope)},
            )
            return CircuitState.OPEN

        logger.debug(
            "[CB] Failure #%d (threshold=%d)",
            failures,
            settings.circuit_breaker_failure_threshold,
            extra={"scope": _scope_token(scope)},
        )
        return CircuitState.CLOSED
    except Exception as exc:
        logger.warning("[CB] Could not record failure: %s", exc, extra={"scope": _scope_token(scope)})
        return CircuitState.CLOSED


def is_open(scope: Optional[str] = None) -> bool:
    """True when Ollama should not be called for this scope."""
    return get_state(scope) == CircuitState.OPEN


def status_dict(scope: Optional[str] = None) -> dict:
    """Return circuit breaker state as dict for status endpoints."""
    failures_key = _scoped_key(_CB_FAILURES_KEY, scope)
    opened_at_key = _scoped_key(_CB_OPENED_AT_KEY, scope)
    try:
        r = _redis()
        state = get_state(scope)
        failures = int(r.get(failures_key) or 0)
        opened_at = r.get(opened_at_key)
        return {
            "state": state.value,
            "failures": failures,
            "threshold": settings.circuit_breaker_failure_threshold,
            "opened_at": float(opened_at) if opened_at else None,
            "scope": _scope_token(scope),
        }
    except Exception:
        logger.warning("[CB] Could not load status, assuming CLOSED", extra={"scope": _scope_token(scope)})
        return {
            "state": CircuitState.CLOSED.value,
            "failures": 0,
            "threshold": settings.circuit_breaker_failure_threshold,
            "scope": _scope_token(scope),
        }
