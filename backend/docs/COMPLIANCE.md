# Compliance

## Supported Regulations

- **GDPR** (EU) - General Data Protection Regulation
- **CCPA** (California) - California Consumer Privacy Act
- **PIPEDA** (Canada) - Personal Information Protection and Electronic Documents Act
- **LGPD** (Brazil) - Lei Geral de Proteção de Dados
- **SOC2** (Global) - Security controls and audit logging

## Compliance Features

### Audit Trail

Every AI operation logged:
- Input/output hashes (cryptographically verifiable)
- Provider used
- Cost incurred
- User who initiated
- Timestamp
- Routing decision

### Compliance Reports

Generate reports for any regulation:

```bash
POST /api/v1/compliance/report
{
  "regulation_id": "gdpr",
  "start_date": "2026-01-01T00:00:00",
  "end_date": "2026-01-31T23:59:59"
}

Response:
{
  "regulation": "gdpr",
  "summary": {
    "total_ai_operations": 150,
    "operations_with_pii": 23,
    "total_cost": "45.23"
  },
  "gdpr_specific": {
    "right_to_access": "Available via /api/v1/privacy/export",
    "right_to_deletion": "Available via /api/v1/privacy/delete",
    "audit_trail": "150 operations logged"
  }
}
```

### Compliance Checking

Automated compliance checks:

```bash
POST /api/v1/compliance/check
{
  "regulation_id": "gdpr"
}

Response:
{
  "compliant": true,
  "regulation": "gdpr",
  "issues": []
}
```

## Audit Log Verification

Verify audit log integrity:

```bash
GET /api/v1/audit/verify/{log_id}

Response:
{
  "verified": true,
  "hash_match": true,
  "log_hash": "abc123..."
}
```

## Data Sovereignty

Choose where data is stored:
- EU (GDPR compliance)
- US (CCPA compliance)
- Other regions

Data never leaves selected region without explicit permission.
