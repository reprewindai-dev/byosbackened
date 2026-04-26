# Privacy & GDPR

## Overview

BYOS AI is privacy-by-design. The primary privacy guarantee is that all AI inference runs on your own hardware — no prompts, responses, or user data are sent to external servers by default. The Groq fallback only activates when Ollama fails, and only if you explicitly set `GROQ_API_KEY`.

---

## Data Flow

```
User request → Your BYOS server (never leaves)
                    ↓
              Ollama (local)  ←── default path, 100% on-premise
                    OR
              Groq (cloud)    ←── only if Ollama circuit opens AND GROQ_API_KEY is set
```

---

## PII Detection & Masking

### Automatic Detection

The PII detector scans for these data types:
- Email addresses
- Phone numbers (US and international formats)
- Social Security Numbers (SSN)
- Credit card numbers (Luhn-validated)
- IP addresses
- Full names (heuristic)
- Dates of birth

### Detection Endpoint

```
POST /api/v1/privacy/detect-pii
{ "text": "Contact Jane Doe at jane@example.com, SSN 123-45-6789" }
→ {
  "has_pii": true,
  "pii_types": ["name", "email", "ssn"],
  "count": 3
}
```

### Masking Strategies

| Strategy | Example Output |
|---|---|
| `redact` | `[EMAIL]`, `[SSN]`, `[PHONE]` |
| `hash` | SHA-256 hex of original value |
| `replace` | Replaced with realistic fake data |
| `partial` | `j***@example.com`, `***-45-****` |

```
POST /api/v1/privacy/mask-pii
{
  "text": "Call John at 555-123-4567",
  "strategy": "redact"
}
→ { "masked_text": "Call [NAME] at [PHONE]" }
```

### Automatic Masking in Audit Logs

When `CONTENT_FILTERING_ENABLED=true`, audit log entries automatically mask detected PII before writing to the database. Raw PII is never persisted in logs.

---

## GDPR Rights Implementation

### Right to Access (Article 15)

Export everything BYOS holds about a user:

```
GET /api/v1/privacy/export
Authorization: Bearer <token>
→ {
  "user": { "id", "email", "created_at", "role" },
  "executions": [ ...all AI calls with tokens, latency, provider... ],
  "audit_logs": [ ...all audit records... ],
  "api_keys": [ ...metadata only, never raw keys... ],
  "jobs": [ ...transcription / extraction jobs... ],
  "export_generated_at": "2026-01-15T14:30:00Z"
}
```

### Right to Erasure (Article 17)

Permanently delete all data for a user and their workspace:

```
POST /api/v1/privacy/delete
{ "confirmation": "DELETE MY ACCOUNT" }
```

Deletes: user record, all execution logs, all audit logs, all conversation memory (Redis), all jobs, all API keys, all cost allocations tied to that workspace.

**This is irreversible.** The confirmation string is required to prevent accidental calls.

### Right to Portability (Article 20)

The export endpoint above returns machine-readable JSON suitable for portability requests.

### Right to Rectification (Article 16)

Users can update their profile data via `PUT /api/v1/auth/profile`.

---

## Data Retention

Configure automatic deletion of old records to minimise stored data:

```
POST /api/v1/privacy/retention-policy
{
  "data_type": "execution_logs",   ← "execution_logs", "audit_logs", "jobs"
  "retention_days": 90
}
```

A Celery beat job (`data_retention_cleanup`) runs daily at midnight and purges all records older than the configured retention window for each workspace.

**Recommended retention periods by industry:**
- General SaaS: 90 days execution logs, 1 year audit logs
- Healthcare: Follow HIPAA — typically 6 years for medical records
- Legal: Consult your jurisdiction — typically 5–7 years
- Finance: Varies by regulation — typically 5–7 years

---

## Consent Management

The platform does not currently implement a consent management UI. For GDPR compliance, you should:
1. Implement a consent banner in your frontend application
2. Store consent records in your own database
3. Use BYOS's `POST /api/v1/privacy/delete` when consent is withdrawn

---

## Privacy Configuration

| Setting | Default | Notes |
|---|---|---|
| `CONTENT_FILTERING_ENABLED` | `true` | Enables PII auto-masking in audit logs |
| `LLM_FALLBACK` | `groq` | Set to `off` if Groq fallback is a data residency concern |
| `AGE_VERIFICATION_REQUIRED` | `false` | Set `true` for adult platforms |
| Data retention | None | Configure per-workspace via retention policy API |

---

## Data Residency

With `LLM_FALLBACK=off` and no `GROQ_API_KEY` set:
- **Zero data leaves your server** for any AI operation
- All inference is local via Ollama
- Suitable for strict data residency requirements (EU, healthcare, government)

With `GROQ_API_KEY` set and `LLM_FALLBACK=groq`:
- Data may leave your server **only** when Ollama circuit is OPEN (failing)
- Groq processes the request under Groq's privacy policy
- Suitable for most commercial use cases where some fallback cloud access is acceptable

---

## CCPA Compliance

BYOS supports CCPA via the same endpoints as GDPR:
- **Right to Know:** `GET /api/v1/privacy/export`
- **Right to Delete:** `POST /api/v1/privacy/delete`
- **Right to Opt-Out:** Disable GROQ fallback with `LLM_FALLBACK=off`

Compliance reports: `POST /api/v1/compliance/report` with `"regulation": "ccpa"`
