---
name: security-agent
description: Playbook for security force agents (102-107). Covers perimeter defense, auth hardening, data protection, threat hunting, and incident response.
---

# Security Force Playbook

## When to Use
Invoke this skill when spinning up any security force agent (Agent-102 through Agent-107).

## Prerequisites
- Access to `byosbackened` repo
- Understanding of OWASP Top 10
- Familiarity with FastAPI security middleware
- Access to dependency scanning tools

## Setup Steps

1. Read your agent mission file from `agents/security-force/agent-{ID}-{name}.md`
2. Read `MASTER_STATE.md` — especially the security section
3. Review current security configuration:
   ```
   backend/app/core/security.py    # Auth, JWT, hashing
   backend/app/middleware/          # CORS, rate limiting
   backend/app/core/config.py      # Secret management
   ```

## Agent Assignments

### Agent-102 (Security Commander)
- Coordinate security team, maintain threat model
- Review all security PRs before merge
- Generate weekly security posture report

### Agent-103 (Perimeter Guard)
- Implement WAF rules, rate limiting, DDoS protection
- Key files: `backend/app/middleware/rate_limit.py`
- Tools: Cloudflare WAF configuration

### Agent-104 (Auth Sentinel)
- Harden JWT implementation, session management
- Audit API key generation and rotation
- Key files: `backend/app/core/security.py`, `backend/app/api/auth.py`

### Agent-105 (Data Guardian)
- Implement encryption at rest and in transit
- Audit key management, PII handling
- Ensure GDPR/data sovereignty compliance
- Key files: `backend/app/core/encryption.py`

### Agent-106 (Threat Hunter)
- Run CVE scans on dependencies
- Perform SAST/DAST analysis
- Key tools: `safety check`, `bandit`, `pip-audit`

```bash
# Dependency vulnerability scan
pip install safety pip-audit bandit
safety check --full-report
pip-audit
bandit -r backend/app/ -f json
```

### Agent-107 (Incident Responder)
- Set up breach detection alerts
- Create incident response playbook
- Define containment procedures

## Security Standards

| Control | Requirement |
|---|---|
| Authentication | JWT with RS256, refresh tokens |
| Authorization | RBAC with role hierarchy |
| Encryption | AES-256 at rest, TLS 1.3 in transit |
| Rate Limiting | 100 req/min per IP, 1000/min per user |
| Input Validation | Pydantic schemas on all endpoints |
| Logging | Structured audit logs, no PII in logs |
| Dependencies | No known CVEs above CVSS 7.0 |

## Completion Checklist
- [ ] Read mission file and MASTER_STATE.md
- [ ] Execute security assessment for assigned domain
- [ ] Document findings with severity ratings
- [ ] Implement fixes for critical/high findings
- [ ] Run security scans to verify fixes
- [ ] Create PR with security improvements
- [ ] Update PROGRESS.md with security posture
