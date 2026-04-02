# Troubleshooting: Metrics Import Error

## Problem

**Error:**
```
ImportError: cannot import name 'get_metrics_collector' from 'core.metrics' (/app/core/metrics/__init__.py)
```

**Symptom:**
- API container keeps restarting (status: `Restarting (1)`)
- Error occurs during application startup when importing middleware

## Root Cause

The `get_metrics_collector` function exists in `core/metrics/collector.py` but was not exported from `core/metrics/__init__.py`.

The middleware (`apps/api/middleware/metrics.py`) tries to import:
```python
from core.metrics import get_metrics_collector
```

But `core/metrics/__init__.py` only exported `MetricsCollector`, not the `get_metrics_collector` function.

## Solution ✅

**Fixed:** Updated `core/metrics/__init__.py` to export `get_metrics_collector`

**Before:**
```python
"""Metrics module."""
from core.metrics.collector import MetricsCollector

__all__ = [
    "MetricsCollector",
]
```

**After:**
```python
"""Metrics module."""
from core.metrics.collector import MetricsCollector, get_metrics_collector

__all__ = [
    "MetricsCollector",
    "get_metrics_collector",
]
```

## Verification

After deploying the fix:

1. **Rebuild the API container:**
   ```bash
   cd /srv/apps/byos_real/infra/docker
   docker compose build --no-cache api
   docker compose up -d api
   ```

2. **Check logs:**
   ```bash
   docker logs --tail 50 byos_real_api
   ```
   
   Should see no import errors, and the API should start successfully.

3. **Verify API is running:**
   ```bash
   docker ps | grep byos_real_api
   ```
   
   Status should be `Up` (not `Restarting`)

4. **Test health endpoint:**
   ```bash
   curl http://localhost:8011/health
   ```
   
   (Adjust port based on your docker-compose.yml configuration)

## Files Changed

- ✅ `core/metrics/__init__.py` - Added `get_metrics_collector` to exports

## Related Files

- `core/metrics/collector.py` - Contains `get_metrics_collector()` function
- `apps/api/middleware/metrics.py` - Imports and uses `get_metrics_collector`
- `apps/api/main.py` - Uses `MetricsMiddleware`

## Next Steps

1. ✅ Fix applied to `core/metrics/__init__.py`
2. ⏭️ Deploy fix to server
3. ⏭️ Rebuild and restart API container
4. ⏭️ Verify API starts successfully
