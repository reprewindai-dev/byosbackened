# Security Architecture

## Zero-Trust Security Model

Every request is verified - no implicit trust.

### Authentication

- JWT tokens with short expiration (30 minutes default)
- Refresh tokens for session management
- Token includes workspace_id and user_id

### Authorization

- Role-based access control (RBAC)
- Workspace-level isolation
- Principle of least privilege

### Encryption

- TLS 1.3 for all connections
- AES-256-GCM for data at rest encryption
- Field-level encryption for sensitive data (PII, API keys)

### Secrets Management

- No secrets in code
- Environment variables or external secret managers
- Automatic secret rotation support
- Secrets audit trail

## Security Features

### API Security

- Rate limiting per workspace
- Request signing (HMAC) for webhooks
- IP whitelisting (optional)
- API key rotation

### Data Protection

- Encrypt sensitive database fields
- Encrypt audit logs
- Secure backup storage

### Security Audit Logging

All security events logged:
- Login attempts (success/failure)
- Permission changes
- API key access
- Suspicious activity

## Security Best Practices

1. **Never log secrets** - Secrets are never logged, even in error messages
2. **Rotate regularly** - API keys and secrets rotated automatically
3. **Monitor access** - All secret access logged for audit
4. **Encrypt everything** - Sensitive data encrypted at rest and in transit
