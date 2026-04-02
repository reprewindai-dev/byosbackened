# Privacy Protection

## Privacy-by-Design

GDPR-compliant privacy protection built into every feature.

### Data Minimization

- Only collect necessary data
- Remove unnecessary fields automatically
- Purpose limitation enforced

### PII Detection & Masking

Automatic detection of:
- Email addresses
- Phone numbers
- Credit card numbers
- Social security numbers
- IP addresses
- Names (via NER)

Masking strategies:
- Full masking: `email@example.com` → `***@***.com`
- Partial masking: `John Doe` → `J*** D***`
- Hashing: For searchable but non-readable data
- Encryption: For data that needs to be readable later

### Data Retention

- Configurable retention policies per workspace
- Automatic deletion after retention period
- Audit logs retained longer (compliance requirement)
- Backup deletion (ensures backups also deleted)

### GDPR Rights

- **Right to Access**: `/api/v1/privacy/export` - Export all user data
- **Right to Deletion**: `/api/v1/privacy/delete` - Delete all user data
- **Data Portability**: Export in JSON/CSV formats

## Privacy Features

### PII Detection

```bash
POST /api/v1/privacy/detect-pii
{
  "text": "Contact john@example.com or call 555-1234"
}

Response:
{
  "detected": [
    {"type": "email", "value": "john@example.com"},
    {"type": "phone", "value": "555-1234"}
  ]
}
```

### PII Masking

```bash
POST /api/v1/privacy/mask-pii
{
  "text": "Contact john@example.com",
  "strategy": "partial"
}

Response:
{
  "masked_text": "Contact j***@e***.com",
  "detected": [...]
}
```

## Compliance

- GDPR compliant
- CCPA compliant
- Data sovereignty support (choose where data is stored)
