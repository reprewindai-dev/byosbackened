"""
Production Gunicorn config for BYOS API.

Tuned for:
- High concurrency (uvicorn workers + uvloop event loop)
- Long-lived connections (keep-alive, large backlog)
- Predictable resource use (worker recycling, memory limits)
"""
import multiprocessing
import os

# ── Bind ─────────────────────────────────────────────────────────────────────
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# ── Workers ──────────────────────────────────────────────────────────────────
# Rule of thumb: (2 * CPU cores) + 1 for sync, but uvicorn workers are async,
# so 2 * cores is plenty. Override with WEB_CONCURRENCY env var.
_default_workers = max(2, multiprocessing.cpu_count() * 2)
workers = int(os.getenv("WEB_CONCURRENCY", _default_workers))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 10000          # recycle workers periodically
max_requests_jitter = 1000    # avoid thundering herd
timeout = 120                 # 2 min for slow LLM calls
graceful_timeout = 30
keepalive = 65                # long keep-alive for HTTP/1.1 reuse

# ── Logging ──────────────────────────────────────────────────────────────────
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'
)

# ── Misc ─────────────────────────────────────────────────────────────────────
preload_app = True            # share imports across workers - faster boot
forwarded_allow_ips = "*"     # honour X-Forwarded-* from reverse proxy
proxy_allow_ips = "*"
