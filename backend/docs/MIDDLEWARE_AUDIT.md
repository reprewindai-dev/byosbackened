# Veklom Backend Middleware Audit

Generated from Windsurf inspection of `apps/api/middleware/`.

## Middleware Stack (Execution Order)

Current order (outermost first):
1. **FastPathMiddleware** - Pure ASGI fast path for hot public endpoints
2. **GzipMiddleware** - Response compression
3. **PerformanceMiddleware** - Caching + keep-alive
4. **CORSMiddleware** - Cross-origin requests
5. **BudgetCheckMiddleware** - Budget enforcement
6. **EdgeRoutingMiddleware** - Edge routing decisions
7. **IntelligentRoutingMiddleware** - Provider selection
8. **MetricsMiddleware** - Request metrics
9. **ZeroTrustMiddleware** - Authentication
10. **RateLimitMiddleware** - Rate limiting
11. **RequestSecurityMiddleware** - Request security tracking
12. **LockerSecurityMiddleware** - IDS, security headers

---

## Individual Middleware Analysis

### 1. FastPathMiddleware
| Property | Value |
|----------|-------|
| **File** | `apps/api/middleware/fast_path.py` |
| **Purpose** | Bypass entire middleware chain for public endpoints |
| **Protected Routes** | `/health`, `/status`, `/`, `/api/v1/docs`, `/api/v1/redoc`, `/api/v1/openapi.json` |
| **Dependencies** | None (outermost layer) |
| **Risk** | public |
| **Recommendation** | **KEEP** - Critical for performance |

**Notes:** Allows unauthenticated access to docs and health. Safe and necessary.

---

### 2. LockerSecurityMiddleware
| Property | Value |
|----------|-------|
| **File** | `apps/api/middleware/locker_security_integration.py` |
| **Purpose** | IDS, rate limiting, security headers |
| **Protected Routes** | All routes (first line of defense) |
| **Dependencies** | Redis |
| **Risk** | public |
| **Recommendation** | **KEEP** - Security critical |

**Notes:** First line of defense, includes IDS and security headers. Must remain.

---

### 3. RequestSecurityMiddleware
| Property | Value |
|----------|-------|
| **File** | `apps/api/middleware/request_security.py` |
| **Purpose** | Request ID generation, IP blocking, brute force protection |
| **Protected Routes** | `/api/v1/auth/login`, `/api/v1/auth/register`, `/api/v1/auth/refresh` |
| **Dependencies** | None (in-memory state) |
| **Risk** | public |
| **Recommendation** | **KEEP** - Security critical |

**Current Behavior:**
- Generates request IDs for audit trails
- Tracks failed auth attempts per IP
- Blocks IPs after 5 failed attempts in 15 minutes
- Adds security headers (X-Request-ID, X-Response-Time with noise)

**Notes:** Critical for security. Keep unchanged.

---

### 4. RateLimitMiddleware
| Property | Value |
|----------|-------|
| **File** | `apps/api/middleware/rate_limit.py` |
| **Purpose** | Per-workspace and per-IP rate limiting |
| **Protected Routes** | All except: `/health`, `/`, `/metrics`, `/status`, `/api/v1/auth/*`, `/api/v1/docs` |
| **Dependencies** | Redis |
| **Risk** | public |
| **Recommendation** | **KEEP** - Critical for availability |

**Current Behavior:**
- Per-workspace limit: 18,000 req/min (300 req/sec)
- Per-IP limit: 6,000 req/min (100 req/sec)
- Auth endpoints: 20 req/min burst limit
- Uses Redis sliding window
- Fails open if Redis unavailable

**Notes:** Essential for DDoS protection. Keep unchanged.

---

### 5. ZeroTrustMiddleware
| Property | Value |
|----------|-------|
| **File** | `core/security/zero_trust.py` |
| **Purpose** | JWT/API Key authentication, tenant isolation |
| **Protected Routes** | All except public_paths list |
| **Dependencies** | Database, Redis |
| **Risk** | authenticated |
| **Recommendation** | **KEEP** - Authentication backbone |

**Current Behavior:**
- Validates JWT tokens from Authorization header
- Validates API keys from X-API-Key header
- Sets `request.state.workspace_id` and `request.state.user`
- Enforces tenant isolation

**Notes:** Core authentication. Must remain. Sets workspace_id used by downstream middleware.

---

### 6. MetricsMiddleware
| Property | Value |
|----------|-------|
| **File** | `apps/api/middleware/metrics.py` |
| **Purpose** | Request metrics collection |
| **Protected Routes** | All routes |
| **Dependencies** | None |
| **Risk** | authenticated |
| **Recommendation** | **KEEP** - Observability critical |

---

### 7. IntelligentRoutingMiddleware
| Property | Value |
|----------|-------|
| **File** | `apps/api/middleware/intelligent_routing.py` |
| **Purpose** | Auto-route requests to optimal provider |
| **Protected Routes** | `/api/v1/transcribe`, `/api/v1/extract` |
| **Dependencies** | ProviderRouter |
| **Risk** | paid |
| **Recommendation** | **KEEP** - Cost optimization |

**Current Behavior:**
- Only applies to transcribe/extract endpoints
- Stores routing constraints in request.state
- Actual routing happens in endpoint handlers

**Notes:** Cost optimization feature. Keep as-is.

---

### 8. EdgeRoutingMiddleware
| Property | Value |
|----------|-------|
| **File** | `apps/api/middleware/edge_routing.py` |
| **Purpose** | Edge routing decisions |
| **Protected Routes** | TBD (currently minimal implementation) |
| **Dependencies** | None |
| **Risk** | authenticated |
| **Recommendation** | **KEEP** - Future extensibility |

---

### 9. BudgetCheckMiddleware
| Property | Value |
|----------|-------|
| **File** | `apps/api/middleware/budget_check.py` |
| **Purpose** | Check budget before expensive operations |
| **Protected Routes** | `/api/v1/transcribe`, `/api/v1/extract`, `/v1/exec`, `/api/v1/ai/*`, `/api/v1/cost/predict` |
| **Dependencies** | Redis, Database, BudgetTracker, CostKillSwitch |
| **Risk** | paid |
| **Recommendation** | **KEEP** - Cost control critical |

**Current Behavior:**
- Checks manual kill switch (Redis)
- Checks global daily cost cap
- Checks workspace daily cost cap
- Checks monthly budget
- Returns 402 if exceeded
- Fails open if Redis down

**Notes:** Essential for cost control. Keep, but will be enhanced with token wallet check.

---

### 10. CORSMiddleware
| Property | Value |
|----------|-------|
| **File** | FastAPI built-in |
| **Purpose** | Cross-origin request handling |
| **Protected Routes** | All routes |
| **Dependencies** | None |
| **Risk** | public |
| **Recommendation** | **KEEP** - Required for frontend |

---

### 11. PerformanceMiddleware + GzipMiddleware
| Property | Value |
|----------|-------|
| **File** | `apps/api/middleware/performance.py` |
| **Purpose** | Caching and compression |
| **Protected Routes** | All routes |
| **Dependencies** | Redis |
| **Risk** | public |
| **Recommendation** | **KEEP** - Performance optimization |

---

## Required New Middleware (Token/Entitlement System)

### 1. EntitlementCheckMiddleware
| Property | Value |
|----------|-------|
| **Purpose** | Check subscription tier before API access |
| **Position** | After ZeroTrustMiddleware, before RateLimitMiddleware |
| **Protected Routes** | All tier-restricted endpoints |
| **Dependencies** | Database (subscriptions table) |
| **Risk** | authenticated |

**Behavior:**
- Look up workspace's current subscription tier
- Check if endpoint requires specific tier
- Return 403 if insufficient tier
- Add entitlement info to request.state

**Endpoint-to-Tier Mapping:**
- `starter`: Basic endpoints (auth, cost/predict, content/scan)
- `pro`: Standard API + insights + billing + routing
- `sovereign`: Kill switch + security + compliance + audit
- `enterprise`: Admin + training + custom endpoints

---

### 2. TokenDeductionMiddleware
| Property | Value |
|----------|-------|
| **Purpose** | Deduct tokens from wallet per request |
| **Position** | After EntitlementCheckMiddleware, before BudgetCheckMiddleware |
| **Protected Routes** | Tokenized endpoints only |
| **Dependencies** | Database (token_wallet table), endpoint_catalog |
| **Risk** | paid |

**Behavior:**
- Load endpoint token cost from endpoint_catalog
- Check wallet balance before execution
- Deduct tokens atomically if sufficient balance
- Return 402 Payment Required if insufficient
- Record transaction to token_ledger
- Add remaining balance to response headers

**Token Cost Lookup:**
```python
endpoint_catalog = {
    "/api/v1/cost/predict": {"token_cost": 25, "plan": "starter"},
    "/api/v1/autonomous/cost/predict": {"token_cost": 50, "plan": "pro"},
    # ... etc
}
```

---

## Updated Middleware Pipeline

```
Request
  ↓
FastPathMiddleware (public endpoints only)
  ↓
LockerSecurityMiddleware (IDS, headers)
  ↓
RequestSecurityMiddleware (request ID, IP block)
  ↓
RateLimitMiddleware (rate limiting)
  ↓
ZeroTrustMiddleware (authentication)
  ↓
**EntitlementCheckMiddleware** (NEW - plan tier check)
  ↓
**TokenDeductionMiddleware** (NEW - token wallet check/deduct)
  ↓
BudgetCheckMiddleware (budget caps)
  ↓
IntelligentRoutingMiddleware (provider selection)
  ↓
EdgeRoutingMiddleware (edge routing)
  ↓
MetricsMiddleware (metrics collection)
  ↓
CORSMiddleware (CORS handling)
  ↓
GzipMiddleware (compression)
  ↓
PerformanceMiddleware (caching)
  ↓
Handler Executes
  ↓
UsageEventWriter (record usage)
  ↓
AuditLogger (audit trail)
  ↓
Response
```

---

## Implementation Notes

### EntitlementCheckMiddleware Logic
```python
async def dispatch(self, request, call_next):
    workspace_id = request.state.workspace_id
    endpoint = request.url.path
    method = request.method
    
    # Look up required plan for this endpoint
    required_plan = endpoint_catalog.get(endpoint, {}).get("plan", "starter")
    
    # Get workspace's current plan
    subscription = get_subscription(workspace_id)
    current_plan = subscription.plan  # starter/pro/sovereign/enterprise
    
    # Check if current plan meets required plan
    plan_hierarchy = ["starter", "pro", "sovereign", "enterprise"]
    if plan_hierarchy.index(current_plan) < plan_hierarchy.index(required_plan):
        return JSONResponse(
            status_code=403,
            content={"detail": f"This endpoint requires {required_plan} plan"}
        )
    
    request.state.required_plan = required_plan
    return await call_next(request)
```

### TokenDeductionMiddleware Logic
```python
async def dispatch(self, request, call_next):
    workspace_id = request.state.workspace_id
    endpoint = request.url.path
    
    # Get token cost from catalog
    token_cost = endpoint_catalog.get(endpoint, {}).get("token_cost", 0)
    if token_cost == 0:
        return await call_next(request)
    
    # Check wallet balance
    wallet = get_wallet(workspace_id)
    if wallet.balance < token_cost:
        return JSONResponse(
            status_code=402,
            content={"detail": f"Insufficient tokens. Required: {token_cost}, Balance: {wallet.balance}"}
        )
    
    # Deduct tokens atomically
    new_balance = wallet.deduct(token_cost)
    
    # Record transaction
    record_token_transaction(
        workspace_id=workspace_id,
        endpoint=endpoint,
        tokens_deducted=token_cost,
        balance_before=wallet.balance + token_cost,
        balance_after=new_balance
    )
    
    # Store balance for response header
    request.state.remaining_tokens = new_balance
    
    response = await call_next(request)
    response.headers["X-Tokens-Remaining"] = str(new_balance)
    return response
```

---

## Migration Strategy

1. **Phase 1**: Create documentation (this file)
2. **Phase 2**: Create new middleware without enabling
3. **Phase 3**: Test middleware in staging
4. **Phase 4**: Enable entitlement middleware (read-only mode)
5. **Phase 5**: Enable token deduction (test mode - no actual deduction)
6. **Phase 6**: Full enablement with monitoring
7. **Phase 7**: Production deployment

---
*Generated: 2026-04-27*
