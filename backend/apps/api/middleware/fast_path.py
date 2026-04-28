"""
Fast-path ASGI middleware (two-tier cached).

Public/health endpoints get a pure-ASGI short-circuit that bypasses the entire
BaseHTTPMiddleware chain. This is the single highest-impact latency win:
each BaseHTTPMiddleware layer adds ~0.5-2 ms of pure overhead, and the chain
is 10+ deep. Fast-path drops well-known public paths to <1 ms.

Two-tier cache:
  L1 — in-process dict (per-worker, sub-microsecond hit)
  L2 — Redis (shared across all gunicorn workers and replicas, sub-millisecond)

L2 makes the cache useful in multi-worker deploys: a /openapi.json computed
by worker 1 is instantly available to workers 2-N without recomputation.

Cloudflare/CDN-friendly: emits `Cache-Control: public, max-age=N` so an
upstream CDN serves further hits without ever touching origin.

Pure ASGI for minimum overhead. Fails open if Redis is unavailable
(L1 still works, just no cross-worker sharing).
"""
from __future__ import annotations

import logging
import os
import time
from typing import Dict, Optional, Tuple

from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


# ─────────────────────────── L1 in-process cache ─────────────────────────────
# path -> (expires_at_monotonic, body, content_type, status_code)
_CACHE: Dict[str, Tuple[float, bytes, str, int]] = {}
_TTL_SECONDS = 30.0
_REDIS_KEY_PREFIX = "fp:"

# Paths that are 100% safe to short-circuit (idempotent, no per-user variance,
# no auth needed). Anything in here returns identical bytes for all callers.
_FAST_GET_PATHS = {
    "/metrics",
}


# ───────────────────────────── L2 Redis client ───────────────────────────────
_redis_client = None
_redis_initialized = False


def _get_redis():
    """Lazy Redis init. Returns client or None (fail-open)."""
    global _redis_client, _redis_initialized
    if _redis_initialized:
        return _redis_client
    _redis_initialized = True
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return None
    try:
        # Prefer the shared pool if available
        try:
            from core.redis_pool import get_redis as _get_pool
            _redis_client = _get_pool()
        except Exception:
            import redis as _redis_pkg
            _redis_client = _redis_pkg.from_url(
                redis_url, socket_timeout=0.25, socket_connect_timeout=0.25
            )
        # Cheap sanity ping
        _redis_client.ping()
        logger.info("FastPath L2 cache: Redis connected")
    except Exception as e:
        logger.warning(f"FastPath L2 cache: Redis unavailable ({e}) — L1 only")
        _redis_client = None
    return _redis_client


def _now() -> float:
    return time.monotonic()


async def _capture_response(app: ASGIApp, scope: Scope, receive: Receive) -> Tuple[int, Dict[str, str], bytes]:
    """Run the inner app and capture status + headers + body."""
    status_code = 500
    headers: Dict[str, str] = {}
    body_chunks: list[bytes] = []

    async def _send(message):
        nonlocal status_code, headers
        if message["type"] == "http.response.start":
            status_code = message["status"]
            headers = {
                k.decode("latin-1").lower(): v.decode("latin-1")
                for k, v in message.get("headers", [])
            }
        elif message["type"] == "http.response.body":
            body = message.get("body", b"")
            if body:
                body_chunks.append(body)

    await app(scope, receive, _send)
    return status_code, headers, b"".join(body_chunks)


class FastPathMiddleware:
    """
    Outermost ASGI middleware. Short-circuits a fixed set of GET endpoints
    with cached bytes and bypasses the entire downstream middleware stack.

    For everything else, just forwards untouched.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "")

        # Only fast-path GET to known-safe public endpoints.
        if method != "GET" or path not in _FAST_GET_PATHS:
            await self.app(scope, receive, send)
            return

        now = _now()

        # ── L1 (in-process) ────────────────────────────────────────────────
        l1 = _CACHE.get(path)
        if l1 is not None and l1[0] > now:
            _, body, content_type, status_code = l1
            await self._send_cached(send, status_code, body, content_type, source="l1")
            return

        # ── L2 (Redis, shared across workers) ──────────────────────────────
        l2 = self._l2_get(path)
        if l2 is not None:
            body, content_type, status_code = l2
            # Promote into L1 so subsequent hits in this worker are sub-µs
            _CACHE[path] = (now + _TTL_SECONDS, body, content_type, status_code)
            await self._send_cached(send, status_code, body, content_type, source="l2")
            return

        # ── Cache miss — compute, write through to L1 and L2 ──────────────
        async def _empty_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        status_code, headers, body = await _capture_response(self.app, scope, _empty_receive)
        content_type = headers.get("content-type", "application/json")

        if 200 <= status_code < 300 and body:
            _CACHE[path] = (now + _TTL_SECONDS, body, content_type, status_code)
            self._l2_set(path, body, content_type, status_code)

        await self._send_cached(send, status_code, body, content_type, source="origin")

    # ───────────────────────────── L2 helpers ────────────────────────────────
    @staticmethod
    def _l2_get(path: str) -> Optional[Tuple[bytes, str, int]]:
        r = _get_redis()
        if r is None:
            return None
        try:
            raw = r.get(_REDIS_KEY_PREFIX + path)
            if not raw:
                return None
            # Format: status\ncontent_type\nbody  (header line, header line, then bytes)
            sep1 = raw.index(b"\n")
            status_code = int(raw[:sep1])
            sep2 = raw.index(b"\n", sep1 + 1)
            content_type = raw[sep1 + 1 : sep2].decode("latin-1")
            body = raw[sep2 + 1 :]
            return body, content_type, status_code
        except Exception as e:
            logger.debug(f"FastPath L2 get failed ({e})")
            return None

    @staticmethod
    def _l2_set(path: str, body: bytes, content_type: str, status_code: int) -> None:
        r = _get_redis()
        if r is None:
            return
        try:
            payload = (
                str(status_code).encode("latin-1") + b"\n"
                + content_type.encode("latin-1") + b"\n"
                + body
            )
            r.setex(_REDIS_KEY_PREFIX + path, int(_TTL_SECONDS), payload)
        except Exception as e:
            logger.debug(f"FastPath L2 set failed ({e})")

    # ──────────────────────────── send helper ───────────────────────────────
    @staticmethod
    async def _send_cached(
        send: Send, status_code: int, body: bytes, content_type: str, source: str = "l1",
    ) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    (b"content-type", content_type.encode("latin-1")),
                    (b"content-length", str(len(body)).encode("latin-1")),
                    (b"x-fast-path", source.encode("latin-1")),
                    # Cloudflare / CDN edges respect this and serve from edge.
                    (b"cache-control", b"public, max-age=30, s-maxage=60"),
                    (b"vary", b"Accept-Encoding"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})
