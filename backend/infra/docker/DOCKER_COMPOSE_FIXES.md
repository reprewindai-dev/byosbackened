# Docker Compose Fixes - Environment Variables

## Issues Fixed

### Bug 1: Nested Variable Substitution in ENCRYPTION_KEY ✅ FIXED

**Problem:**
- Pattern `ENCRYPTION_KEY=${ENCRYPTION_KEY:-${SECRET_KEY}}` uses nested variable substitution
- Docker Compose doesn't support nested variable substitution
- When `ENCRYPTION_KEY` is not set, the fallback would be the literal string `${SECRET_KEY}` instead of the actual SECRET_KEY value
- This breaks encryption key initialization at runtime

**Fix Applied:**
Changed from:
```yaml
- ENCRYPTION_KEY=${ENCRYPTION_KEY:-${SECRET_KEY}}
```

To:
```yaml
- ENCRYPTION_KEY=${ENCRYPTION_KEY}
```

**Impact:**
- If `ENCRYPTION_KEY` is set in environment, it will be used
- If `ENCRYPTION_KEY` is not set, it will be empty string
- **Application code must handle fallback:** If `ENCRYPTION_KEY` is empty/None, application should use `SECRET_KEY` as fallback

**Note:** This is the correct approach for Docker Compose. The application code should handle the fallback logic, not Docker Compose.

---

### Bug 2: Missing ALGORITHM in Worker Service ✅ FIXED

**Problem:**
- The `worker` service was missing the `ALGORITHM` environment variable
- The `api` service has `ALGORITHM=${ALGORITHM:-HS256}`
- If worker processes tasks involving JWT token validation or creation, it would fail at runtime due to missing configuration

**Fix Applied:**
Added `ALGORITHM` environment variable to worker service:

```yaml
# Security
- SECRET_KEY=${SECRET_KEY}
- ENCRYPTION_KEY=${ENCRYPTION_KEY}
- ALGORITHM=${ALGORITHM:-HS256}  # ← Added this
```

**Impact:**
- Both `api` and `worker` services now have consistent JWT algorithm configuration
- Worker can now properly validate/create JWT tokens
- Default algorithm is `HS256` if not specified

---

## Verification

Both services now have consistent security configuration:

### API Service (lines 87-91)
```yaml
# Security
- SECRET_KEY=${SECRET_KEY}
- ENCRYPTION_KEY=${ENCRYPTION_KEY}
- ALGORITHM=${ALGORITHM:-HS256}
- ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-30}
```

### Worker Service (lines 150-153)
```yaml
# Security
- SECRET_KEY=${SECRET_KEY}
- ENCRYPTION_KEY=${ENCRYPTION_KEY}
- ALGORITHM=${ALGORITHM:-HS256}  # ← Now matches API service
```

---

## Application Code Requirement

**Important:** The application code must handle the `ENCRYPTION_KEY` fallback:

```python
# Example implementation
encryption_key = os.getenv("ENCRYPTION_KEY") or os.getenv("SECRET_KEY")
if not encryption_key:
    raise ValueError("Either ENCRYPTION_KEY or SECRET_KEY must be set")
```

This ensures that if `ENCRYPTION_KEY` is not explicitly set, the application will use `SECRET_KEY` as the fallback, maintaining backward compatibility.

---

## Files Changed

- ✅ `infra/docker/docker-compose.yml` - Fixed both issues

---

## Testing

After deploying these fixes:

1. **Test ENCRYPTION_KEY fallback:**
   - Set only `SECRET_KEY` in `.env`
   - Verify application uses `SECRET_KEY` for encryption
   - Set both `SECRET_KEY` and `ENCRYPTION_KEY` in `.env`
   - Verify application uses `ENCRYPTION_KEY` for encryption

2. **Test ALGORITHM in worker:**
   - Start worker service
   - Verify worker can process JWT-related tasks
   - Check logs for any JWT algorithm errors

---

## Summary

✅ **Bug 1 Fixed:** Removed nested variable substitution from `ENCRYPTION_KEY`  
✅ **Bug 2 Fixed:** Added `ALGORITHM` environment variable to worker service  
✅ **Consistency:** Both services now have matching security configuration
