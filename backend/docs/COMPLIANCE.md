# Compliance

## Overview

BYOS AI generates cryptographically verifiable audit trails that satisfy GDPR, CCPA, SOC2, and HIPAA-adjacent requirements. Every AI operation produces an immutable HMAC-SHA256 log record that proves what ran, when, who authorised it, and what it cost.

---

## Immutable Audit Logs

### How They Work

Every call to `POST /v1/exec` and every AI operation writes an audit record to `ai_audit_logs`:

```
{
  id:              UUID (primary key)
  workspace_id:    tenant identifier
  user_id:         who initiated (nullable for API key calls)
  operation_type:  "inference", "transcribe", "extract"
  provider:        "ollama" | "groq"
  model:           "qwen2.5:3b"
  input_tokens:    int
  output_tokens:   int
  cost:            Decimal(10,6)
  latency_ms:      int
  hmac_hash:       SHA-256 HMAC of record contents
  previous_hash:   HMAC of the previous record (log chaining)
  created_at:      timestamp
}
```

### Why They Cannot Be Tampered With

1. **HMAC-SHA256 hash** covers all record fields — any modification changes the hash
2. **Chained hashes** — each record includes the hash of the previous record (like a blockchain). Modifying any record breaks the chain for all subsequent records
3. **No UPDATE permission** — the application user has INSERT/SELECT only on audit tables
4. **Verified on read** — `GET /api/v1/audit` re-computes HMAC on retrieval and flags any mismatch

---

## Querying Audit Logs

```
GET /api/v1/audit
  ?start_date=2026-01-01
  &end_date=2026-01-31
  &operation_type=inference
  &provider=ollama
  &limit=100
  &offset=0

→ [{
  "id": "...",
  "operation_type": "inference",
  "provider": "ollama",
  "model": "qwen2.5:3b",
  "input_tokens": 142,
  "output_tokens": 287,
  "cost": "0.000000",
  "latency_ms": 1840,
  "hmac_hash": "sha256:abc123...",
  "hmac_valid": true,          ← false if record was tampered
  "created_at": "2026-01-15T14:30:00Z"
}]
```

---

## On-Demand Compliance Reports

```
POST /api/v1/compliance/report
{
  "regulation": "gdpr",   ← "gdpr" | "ccpa" | "soc2"
  "start_date": "2026-01-01",
  "end_date": "2026-01-31"
}

→ {
  "regulation": "GDPR",
  "period": "2026-01-01 to 2026-01-31",
  "compliance_score": 97,
  "summary": {
    "total_operations": 14823,
    "data_types_processed": ["text", "audio"],
    "pii_detected_and_masked": 342,
    "deletion_requests_fulfilled": 2,
    "export_requests_fulfilled": 5
  },
  "findings": [
    {
      "area": "Data Retention",
      "status": "compliant",
      "detail": "All records within configured retention window"
    }
  ],
  "recommendations": [...],
  "generated_at": "2026-01-31T23:59:00Z"
}
```

---

## GDPR Compliance Checklist

| Requirement | BYOS Implementation | Endpoint |
|---|---|---|
| Right to Access (Art. 15) | Full data export | `GET /api/v1/privacy/export` |
| Right to Erasure (Art. 17) | Complete account deletion | `DELETE /api/v1/privacy/delete-account` |
| Right to Portability (Art. 20) | JSON export | `GET /api/v1/privacy/export` |
| Right to Rectification (Art. 16) | Profile update | `PUT /api/v1/auth/profile` |
| Data Minimisation (Art. 5) | PII masking, retention policies | `POST /api/v1/privacy/retention-policy` |
| Audit Trail | HMAC-SHA256 chained logs | `GET /api/v1/audit` |
| Lawful Basis Documentation | Compliance reports | `POST /api/v1/compliance/report` |

---

## SOC2 Compliance

BYOS supports SOC2 Type II audit evidence across all five Trust Service Criteria:

| Criteria | Implementation |
|---|---|
| **Security** | Zero-trust, MFA, AES-256, RBAC, security event log |
| **Availability** | Circuit breaker (self-healing), health monitoring, SLA tracking |
| **Confidentiality** | Data isolation (RLS), encryption at rest, API key scoping |
| **Processing Integrity** | HMAC audit trail, cost prediction accuracy tracking, quality scoring |
| **Privacy** | GDPR rights implementation, PII masking, retention policies |

Generate SOC2 evidence report: `POST /api/v1/compliance/report` with `"regulation": "soc2"`

---

## HIPAA-Adjacent Controls

BYOS does not certify HIPAA compliance (requires a BAA with a covered entity). However, the following controls support HIPAA-adjacent deployments:

| Control | Implementation |
|---|---|
| Access Controls | RBAC, MFA, account lockout |
| Audit Controls | Immutable HMAC-SHA256 audit logs |
| Integrity Controls | Log chaining, HMAC verification |
| Transmission Security | TLS 1.3 in production |
| Minimum Necessary | PII masking, data minimisation |
| Data Disposal | GDPR deletion, retention policies |
| PHI Never Leaves Premises | Local Ollama inference, `LLM_FALLBACK=off` option |

For true HIPAA compliance, consult legal counsel and execute a Business Associate Agreement with your hosting provider.

---

## AI Quality Scoring (Audit Evidence)

Every AI response is scored for quality dimensions. Scores are stored in audit logs and can be queried as evidence that the AI system is performing as expected:

```
GET /api/v1/audit/{log_id}/quality
→ {
  "relevance": 0.92,
  "accuracy": 0.88,
  "coherence": 0.95,
  "completeness": 0.81,
  "overall": 0.89
}
```

---

## AI Explainability (Audit Evidence)

For any routing or cost decision, you can retrieve a human-readable explanation:

```
GET /api/v1/explain/routing/{decision_id}
→ {
  "decision": "ollama selected",
  "reasoning": "ollama offers $0.00 cost, meets quality threshold 0.85 >= 0.80...",
  "confidence": 0.94
}
```

This satisfies explainability requirements in regulated industries where automated decisions must be documented.
