# Release v1.0.0 Handoff

**Release Date**: [To be filled by deploy team]  
**Version**: v1.0.0  
**Status**: Ready for Staging Deployment

## File Inventory

### Deployment Scripts (6 scripts in `backend/infra/scripts/`)

1. `tag-release.sh` - Creates git tags for releases
2. `prepare-staging-env.sh` - Prepares staging environment configuration
3. `deploy-staging.sh` - Deploys to staging environment
4. `run-verification-tests.sh` - Runs verification tests and archives logs
5. `canary-deployment.sh` - Manages canary deployment flags
6. `monitor-canary.sh` - Comprehensive canary monitoring

### Documentation

- `backend/infra/scripts/README.md` - Script usage documentation
- `backend/docs/DEPLOYMENT_GUIDE.md` - Complete deployment guide

### Configuration

- `backend/.gitattributes` - Enforces LF line endings for shell scripts (prevents CRLF issues on Windows)

## Quick Start - Staging Deployment

### Prerequisites

- Linux deployment environment (scripts require bash)
- Docker and Docker Compose installed
- Git repository access
- Python environment with pytest
- Staging server/environment access

### Command Sequence

```bash
# Navigate to repo root
cd backend

# 1. Tag release
./infra/scripts/tag-release.sh v1.0.0 "Production-ready release: Autonomous Backend Orchestration & Edge Architecture"
git push origin v1.0.0

# 2. Prepare staging environment
./infra/scripts/prepare-staging-env.sh
# Edit .env.staging with actual values (SECRET_KEY, DATABASE_URL, alert channels, budget caps, etc.)

# 3. Deploy to staging
./infra/scripts/deploy-staging.sh v1.0.0

# 4. Run verification tests
./infra/scripts/run-verification-tests.sh

# 5. Review verification results
cd deployment-logs
cat */VERIFICATION_SUMMARY.md

# 6. Enable canary deployment (select test workspace first)
./infra/scripts/canary-deployment.sh <workspace_id> enable

# 7. Monitor canary workspace (4 hours)
./infra/scripts/monitor-canary.sh <workspace_id> 240

# 8. If successful, canary flags are already enabled globally
#    Monitor all workspaces for 24 hours

# 9. If issues detected, disable immediately
./infra/scripts/canary-deployment.sh <workspace_id> disable
```

## Evidence Bundle Requirements

After staging deployment, **REQUIRED** to provide:

1. **Verification Logs Archive**:
   ```bash
   cd deployment-logs
   tar -czf v1.0.0-staging-evidence-$(date +%Y%m%d).tar.gz */
   ```
   - Must include all test outputs
   - Must include VERIFICATION_SUMMARY.md
   - Must verify no secrets leaked (check scrubbing worked)

2. **Canary Monitoring Results**:
   - `deployment-logs/canary-monitoring-*/success_criteria.md`
   - Must show PASS/FAIL verdict
   - Must include exit code (0 = PASS, 1 = FAIL)

3. **Deployment Logs**:
   - API startup logs (verify "Production configuration validated successfully")
   - Migration logs (verify schema at head)
   - Health check results

**Attach evidence bundle to this release ticket before proceeding to production.**

## Production Deployment

**Only proceed if staging passes all checks.**

Use the same command sequence with production environment:

```bash
# 1. Use production .env source (not .env.staging)
#    Create .env.production with production values

# 2. Deploy using same scripts
./infra/scripts/deploy-staging.sh v1.0.0
# (Script name is same, but it reads from .env.production if configured)

# 3. Follow same verification and canary process
```

## Post-Deployment Checklist

- [ ] All verification tests passed
- [ ] No secrets leaked in logs (verified)
- [ ] Database schema at head (verified)
- [ ] Kill switches tested and working (< 1s response, behavioral change verified)
- [ ] Canary monitoring shows PASS verdict
- [ ] Evidence bundle attached to release ticket
- [ ] Production deployment completed (if staging passed)
- [ ] 24-hour monitoring period completed
- [ ] No critical issues reported

## Critical Safety Checks

The deployment scripts include 8 safety checks:

1. Strict bash mode (`set -euo pipefail`)
2. Idempotent deployment (safe to re-run)
3. Git tag validation (branch check, overwrite protection)
4. Environment leak prevention (secrets scrubbed from logs)
5. Migration safety (aborts on failure, verifies schema at head)
6. Canary scope warning (explicit global flag warning)
7. Real kill switch test (verifies behavioral change, not just flag toggle)
8. Monitoring exit criteria (PASS/FAIL with exit codes)

## Troubleshooting

See detailed guides:
- `backend/infra/scripts/README.md` - Script-specific troubleshooting
- `backend/docs/DEPLOYMENT_GUIDE.md` - Complete troubleshooting section

## Post-Lock Reopen Criteria

Only reopen this ticket if one of these occurs:

1. **Tag discipline broken** - Tag created on wrong branch or overwritten without --force
2. **Secrets leaked in logs** - Environment variables visible in archived logs
3. **Migrations not at head** - Schema mismatch after deployment
4. **Kill switch doesn't stop behavior** - Response time > 1s or no behavioral change

All other issues: Document, create ticket, fix in next release.

## Contact

For deployment questions, refer to:
- Deployment Guide: `backend/docs/DEPLOYMENT_GUIDE.md`
- Script Documentation: `backend/infra/scripts/README.md`
- Runbook: `backend/docs/RUNBOOK.md`

---

**Ready for handoff to deploy team.**
