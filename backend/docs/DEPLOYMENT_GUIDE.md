# Staging Deployment and Canary Release Guide

This guide walks through the complete process of deploying to staging, running verification tests, and executing a controlled canary deployment.

## Overview

The deployment process consists of three phases:

1. **Tag Release and Deploy to Staging** - Create release tag and deploy with production environment variables
2. **Run Verification Tests** - Execute all verification commands and save outputs
3. **Controlled Canary Deployment** - Enable canary flags, monitor, then open to all workspaces

## Prerequisites

- Git repository access
- Staging server/environment access
- Docker and Docker Compose installed
- Python environment with pytest
- All required environment variables prepared

## File Inventory

**Deployment Scripts** (6 scripts in `backend/infra/scripts/`):
- `tag-release.sh`
- `prepare-staging-env.sh`
- `deploy-staging.sh`
- `run-verification-tests.sh`
- `canary-deployment.sh`
- `monitor-canary.sh`

**Documentation**:
- `backend/infra/scripts/README.md` - Script usage documentation
- `backend/docs/DEPLOYMENT_GUIDE.md` - Complete deployment guide

**Configuration**:
- `backend/.gitattributes` - Enforces LF line endings for shell scripts

## Phase 1: Tag Release and Deploy to Staging

### Step 1.1: Create Release Tag

```bash
cd backend
./infra/scripts/tag-release.sh v1.0.0 "Production-ready release: Autonomous Backend Orchestration & Edge Architecture"
git push origin v1.0.0
```

**Note**: Replace `v1.0.0` with your actual version number following semantic versioning.

### Step 1.2: Prepare Staging Environment

```bash
./infra/scripts/prepare-staging-env.sh
```

This will create or edit `.env.staging` with all required variables. You must fill in:

- **Critical Secrets**: `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`
- **Alert Channels**: At least one of `ALERT_EMAIL_TO`, `SLACK_WEBHOOK_URL`, `PAGERDUTY_INTEGRATION_KEY`
- **Budget Caps**: `GLOBAL_DAILY_COST_CAP`, `DEFAULT_WORKSPACE_DAILY_CAP`
- **Feature Flags**: All default to `false` (will enable for canary later)
- **S3/MinIO**: Connection details
- **AI Providers**: API keys

**Important**: Set `DEBUG=false` for production-like validation.

### Step 1.3: Deploy to Staging

```bash
./infra/scripts/deploy-staging.sh v1.0.0
```

This script will:
1. Checkout the specified tag
2. Load environment variables from `.env.staging`
3. Build and start Docker containers
4. Run database migrations
5. Verify deployment health

**Verification**:
- Health check: `curl http://localhost:8000/health`
- Check logs: `docker logs byos_api | tail -50`
- Should see: "✅ Production configuration validated successfully"

## Phase 2: Run Verification Tests

### Step 2.1: Execute Verification Tests

```bash
./infra/scripts/run-verification-tests.sh
```

This will run all verification tests and save outputs to `deployment-logs/<timestamp>/`:

1. Final checklist (`tests/qa/final_checklist.py`)
2. Tenant isolation (`tests/test_tenant_isolation.py`)
3. Migration reversibility (`tests/test_migrations.py`)
4. Alert routing (`tests/alerts/test_alert_routing.py`)
5. Backup/restore smoke test (`tests/backup/test_restore_smoke.py`)
6. Load test (`tests/load/load_test.py`)
7. Feature flags check
8. Startup validation check
9. Prometheus metrics check
10. Database connection test

### Step 2.2: Review Results

```bash
cd deployment-logs
ls -la
cat */VERIFICATION_SUMMARY.md
```

Review all log files to ensure:
- ✅ All tests passed
- ✅ No critical errors in logs
- ✅ Feature flags loaded correctly
- ✅ Startup validation passed
- ✅ Metrics endpoint accessible
- ✅ Database connection working

### Step 2.3: Archive Logs

```bash
cd deployment-logs
tar -czf staging-verification-$(date +%Y%m%d_%H%M%S).tar.gz */
```

**Deliverable**: Archive file with all verification logs and summary report.

## Phase 3: Controlled Canary Deployment

### Step 3.1: Select Test Workspace

Identify a single workspace ID for canary testing:
- Should have existing traffic/data
- Document: `CANARY_WORKSPACE_ID=<workspace-uuid>`

### Step 3.2: Enable Canary Flags

```bash
./infra/scripts/canary-deployment.sh <workspace_id> enable
```

This will:
- Enable `CANARY_DEPLOYMENT_ENABLED=true`
- Enable `AUTONOMOUS_ROUTING_ENABLED=true`
- Restart API service
- Verify flags are enabled

**Note**: Feature flags are global, but canary deployment routes ~10% of traffic to canary models automatically.

### Step 3.3: Monitor Canary Workspace

#### Option A: Quick Monitoring

```bash
./infra/scripts/canary-deployment.sh <workspace_id> monitor
```

This provides a quick status check of:
- Cost monitoring
- Feature flags status
- Kill switch test

#### Option B: Comprehensive Monitoring

```bash
./infra/scripts/monitor-canary.sh <workspace_id> 240  # 4 hours
```

This runs periodic checks every 5 minutes for the specified duration:
- Cost status
- Feature flags
- Kill switch response time (every 30 minutes)
- Generates monitoring logs and summary

### Step 3.4: Verify Success Criteria

**Must Pass**:
- ✅ No cross-tenant data access
- ✅ Cost caps enforced correctly (no leaks)
- ✅ Alerts firing correctly (test alert received)
- ✅ Kill switches take effect instantly (< 1 second)
- ✅ Latency within acceptable range (p95 < baseline + 20%)
- ✅ Error rate < 1%
- ✅ Routing decisions being logged correctly

**If Any Criteria Fail**: Disable canary flags immediately:
```bash
./infra/scripts/canary-deployment.sh <workspace_id> disable
```

### Step 3.5: Open to All Workspaces

**If Canary Successful**:

Flags are already enabled globally. Monitor for 24 hours:
- Cost across all workspaces
- Latency metrics
- Error rates
- Anomaly detection

**Documentation**:
- Update deployment log with canary results
- Document any issues encountered
- Update runbook if procedures changed

## Post-Deployment Monitoring

### Critical Metrics (First 48 Hours)

1. **Cost Guardrails**:
   - Daily cost per workspace
   - Global daily cost
   - Cost cap enforcement events

2. **Tenant Isolation**:
   - Cross-tenant access attempts (should be 0)
   - Workspace-scoped queries (all should include workspace_id)

3. **Alert Routing**:
   - Alert delivery success rate
   - Alert latency (time to notification)

4. **Kill Switch Effectiveness**:
   - Time to disable feature (< 1 second)
   - Feature disable propagation (all instances)

## Rollback Procedure

**If Critical Issues Detected**:

```bash
# 1. Disable all autonomous features (nuclear option)
docker exec -it byos_api python -c "
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
flags.disable_all_autonomous()
"

# 2. Rollback database migration (if needed)
docker exec -it byos_api alembic downgrade -1

# 3. Rollback ML models (if needed)
docker exec -it byos_api python -c "
from core.autonomous.ml_models.cost_predictor import get_cost_predictor_ml
from db.session import SessionLocal
db = SessionLocal()
predictor = get_cost_predictor_ml()
predictor.rollback_to_previous_model(db=db)
"
```

## Legitimate Reopen Triggers

Only reopen if one of these occurs:

1. **Cross-Tenant Read/Write Bug**: Workspace A can access Workspace B's data
2. **Cost Cap Enforcement Leak**: Operations proceed despite exceeding caps
3. **Alert Routing Not Firing**: Alerts not delivered in real infrastructure
4. **Rollback/Kill Switches Not Taking Effect**: Changes don't apply within 1 second

**All Other Issues**: Document, create ticket, fix in next release.

## Troubleshooting

### Deployment Fails

- Check Docker logs: `docker logs byos_api`
- Verify environment variables: `cat .env.staging`
- Ensure database is accessible: `docker exec byos_postgres psql -U postgres -d byos_ai -c "SELECT 1;"`
- Check startup validation: `docker logs byos_api | grep "Production configuration"`

### Verification Tests Fail

- Review individual test log files in `deployment-logs/`
- Check if services are running: `docker ps`
- Verify database migrations: `docker exec byos_api alembic current`
- Run tests individually: `pytest tests/test_tenant_isolation.py -v`

### Canary Monitoring Issues

- Verify workspace ID is correct
- Check feature flags: `docker exec byos_api python -c "from core.autonomous.feature_flags import get_feature_flags; print(get_feature_flags().get_all_flags())"`
- Review monitoring logs: `cat deployment-logs/canary-monitoring-*/success_criteria.md`
- Check routing stats: `curl http://localhost:8000/api/v1/autonomous/routing/stats?workspace_id=<workspace_id>`

## Timeline Estimate

- **Phase 1** (Tag & Deploy): 1-2 hours
- **Phase 2** (Verification): 2-3 hours
- **Phase 3** (Canary): 4-6 hours monitoring + 24 hours full rollout
- **Total**: ~30-35 hours (can be parallelized)

## Success Criteria

- ✅ All verification tests pass
- ✅ Canary deployment successful with no critical issues
- ✅ Monitoring confirms system stability
- ✅ Ready for production deployment

## Related Documentation

- [Runbook](RUNBOOK.md) - Emergency procedures and troubleshooting
- [Production Ready Summary](../PRODUCTION_READY_SUMMARY.md) - Verification checklist
- [Deployment Scripts](../infra/scripts/README.md) - Script documentation
