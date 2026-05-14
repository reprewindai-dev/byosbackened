# Security Architecture

## Overview

BYOS AI implements a zero-trust security model. Every request is authenticated and authorised before any data is touched. No implicit trust exists anywhere in the stack.

---

## Authentication

### JWT Tokens
- Short-lived access tokens (default: 30 minutes)
- Long-lived refresh tokens (default: 30 days)
- Token payload includes: `user_id`, `workspace_id`, `role`
- Algorithm: HS256 (configurable via `ALGORITHM` env var)

### API Keys
- Format: `byos_<random-hex>`
- Stored as SHA-256 hash in Postgres — never the raw key
- Scoped per workspace
- Optional expiry (`expires_at`)
- Revocable instantly via `DELETE /api/v1/auth/api-keys/{id}`
- Seeded dev key generated automatically by `start.ps1`

### MFA (TOTP)
- Setup: `POST /api/v1/auth/mfa/setup` → returns QR code URL + secret
- Works with any TOTP app (Google Authenticator, Authy, 1Password)
- Once enabled, `mfa_code` is required on every login
- Verify setup: `POST /api/v1/auth/mfa/verify` with a valid 6-digit code

---

## Zero-Trust Middleware

`ZeroTrustMiddleware` runs on every protected route:

1. Extract `Authorization: Bearer <token>` or `X-API-Key: byos_...`
2. Validate signature / hash against database
3. Resolve workspace and user from token
4. Check user `status` is `active` (not suspended or deleted)
5. Attach workspace context to request state
6. Reject with 401/403 on any failure — no partial results

Routes exempt from zero-trust: `/` (landing), `/status`, `/health`, `/api/v1/docs`, `/api/v1/subscriptions/webhook`

---

## Perimeter Security

Veklom uses layered perimeter controls before route logic is allowed to matter:

1. Cloudflare/WAF blocks commodity scans, bot floods, suspicious countries/ASNs, and known exploit payloads at the edge.
2. Coolify/Traefik or the deployment proxy terminates traffic and forwards only HTTPS traffic to the application container.
3. `core.security.client_ip.get_client_ip()` only trusts `CF-Connecting-IP`, `X-Real-IP`, or `X-Forwarded-For` when the immediate peer is a trusted proxy.
4. `LockerSecurityMiddleware` applies IDS signatures, per-IP rate limiting, security headers, and security-event logging.
5. `RequestSecurityMiddleware` applies request IDs, auth brute-force blocking, and clean audit correlation.
6. `ZeroTrustMiddleware` authenticates/authorizes the resolved user, workspace, and API key before tenant data is touched.

### Trusted Proxy Rules

Forwarded client-IP headers are never trusted from direct internet callers. By default, only loopback and private proxy networks are trusted:

- `127.0.0.0/8`
- `::1/128`
- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`

Production overrides:

| Env Var | Purpose |
|---|---|
| `TRUSTED_PROXY_CIDRS` | Comma-separated proxy CIDRs allowed to provide forwarding headers |
| `TRUSTED_PROXY_IPS` | Comma-separated exact proxy IPs allowed to provide forwarding headers |

Operational rule: origin access should be locked so public traffic reaches the backend only through Cloudflare and the deployment proxy. Direct origin exposure is treated as a misconfiguration.

---

## Role-Based Access Control (RBAC)

| Role | Capabilities |
|---|---|
| `admin` | Full access including user management, workspace config, admin panel |
| `member` | Use AI endpoints, manage own API keys, view own logs |
| `viewer` | Read-only: logs, dashboards, audit records |

Role is enforced at the route level via the `get_current_user` dependency.

---

## Encryption

### AES-256-GCM (at rest)
- Field-level encryption for sensitive database columns
- Separate `ENCRYPTION_KEY` environment variable (must differ from `SECRET_KEY`)
- Encrypted fields: stored API key metadata, PII-tagged fields, sensitive workspace settings
- Module: `core/security/encryption.py` → `encrypt_field()` / `decrypt_field()`

### TLS (in transit)
- All production traffic via HTTPS (Nginx + Certbot, or Caddy)
- TLS 1.2 minimum, TLS 1.3 preferred
- HTTP→HTTPS redirect enforced

---

## Security Events

All security-relevant events are logged to the `security_events` table with:
- Event type and threat classification
- IP address, user agent, timestamp
- AI confidence score (0–1) for automated detection
- AI recommendations for response action
- Resolution status and notes

### Tracked Event Types

| Threat Type | Description |
|---|---|
| `brute_force` | Repeated failed login attempts |
| `suspicious_login` | Login from unusual location/device |
| `unauthorized_access` | Request to resource without permission |
| `rate_limit_abuse` | Excessive request volume |
| `sql_injection` | SQL injection pattern detected in input |
| `xss` | Cross-site scripting pattern detected |
| `data_exfiltration` | Unusual bulk data export |
| `anomaly` | ML-detected behavioural anomaly |

### Security Score
`GET /api/v1/security/stats` returns a 0–100 security score calculated from:
- Open critical events (heavy negative weight)
- Open high-severity events
- Resolution rate
- Time-to-resolve average

---

## Rate Limiting

Redis sliding-window rate limiting enforced per workspace:
- Per-minute, per-hour, per-day windows configurable via routing policies
- Exceeded limits return HTTP 429
- Abuse events logged automatically when limits are hit repeatedly

---

## Account Security

| Setting | Default | Env Var |
|---|---|---|
| Max failed logins before lockout | 10 | `MAX_FAILED_LOGIN_ATTEMPTS` |
| Lockout duration | 30 min | `ACCOUNT_LOCKOUT_MINUTES` |

---

## API Security Best Practices

1. **Never log secrets** — API keys are logged only as their SHA-256 hash
2. **Rotate keys regularly** — use expiry dates on production API keys
3. **Scope keys** — create separate keys for each integration
4. **Monitor access** — review `GET /api/v1/security/events` weekly
5. **Enable MFA** — for all admin accounts in production
6. **Set CORS** — `CORS_ORIGINS` must list only your actual frontend domains in production
