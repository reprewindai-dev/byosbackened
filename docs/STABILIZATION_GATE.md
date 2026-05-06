# Veklom Stabilization Gate

This is the pre-freeze operating gate for the backend and workspace product.
Do not treat the system as frozen until this checklist is green.

## Allowed Work During Stabilization

- Security hardening
- Bug fixes
- Route/auth/tenant isolation fixes
- Production deploy and canary fixes
- Marketplace content/admin-flow updates
- Documentation that records real operational controls

## Blocked Work During Stabilization

- Rewriting pricing, trial logic, subscriptions, marketplace commerce, auth, or `/v1/exec`
- Adding broad new product surfaces without route-security review
- Reintroducing tracked `.env` files, API keys, bytecode, cache directories, or local deploy scratch files
- Making public claims that are not backed by a route, test, or production canary

## Required Gates

Run locally before pushing:

```powershell
python -m ruff check backend/scripts/audit_route_security.py backend/tests/test_route_security_audit.py
powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/check_secrets.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/check_repo_hygiene.ps1
cd backend
python -m pytest tests/test_route_security_audit.py tests/test_middleware_edges.py tests/test_perimeter_client_ip.py tests/test_internal_operators.py -q
```

CI must pass on `main`:

- CI
- Secret Scan
- Dependency Security Audit
- Docker Build
- Deploy & Health Check
- Backend Deploy

## Production Canaries

Expected public responses:

```text
GET /health                                                     -> 200
GET /api/v1/edge/demo/summary                                  -> 200
GET /api/v1/edge/demo/infrastructure?scenario=network&live=false -> 200
GET /api/v1/edge/demo/infrastructure?scenario=machine&live=false -> 200
```

Expected protected responses without auth:

```text
GET /api/v1/edge/protocol/snmp             -> 401
GET /api/v1/edge/protocol/modbus           -> 401
GET /api/v1/internal/operators/overview    -> 401
GET /api/v1/auth/api-keys                  -> 401
```

## External Audit Focus

Ask auditors to verify:

- No route in sensitive families is public unless explicitly documented.
- Users can only access their own workspace-scoped data.
- Internal operator routes cannot be reached with customer API keys.
- Public demo routes do not allow arbitrary target/host/IP probing.
- Marketplace public browsing is read-only; vendor/admin writes require auth.
- Secrets and generated files are not committed.
- Production canaries match the expected status codes above.

## Freeze Criteria

The system can move from stabilization to maintenance-only when:

- Two independent audits report no critical/high authorization findings.
- CI and deploy workflows are green on latest `main`.
- Production canaries pass after the latest deploy.
- Leaked/previously exposed provider keys are rotated.
- Direct origin access is blocked so public traffic reaches the backend through the approved edge/proxy path.
