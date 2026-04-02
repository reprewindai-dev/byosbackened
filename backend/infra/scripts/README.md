# Deployment Scripts

This directory contains scripts for staging deployment and canary release management.

## Scripts

This directory contains **6 deployment scripts**:

1. `tag-release.sh` - Creates git tags for releases
2. `prepare-staging-env.sh` - Prepares staging environment configuration
3. `deploy-staging.sh` - Deploys to staging environment
4. `run-verification-tests.sh` - Runs verification tests and archives logs
5. `canary-deployment.sh` - Manages canary deployment flags
6. `monitor-canary.sh` - Comprehensive canary monitoring

### `tag-release.sh`
Creates a git tag for release versioning.

**Usage:**
```bash
./tag-release.sh [version] [message]
```

**Example:**
```bash
./tag-release.sh v1.0.0 "Production-ready release"
```

### `prepare-staging-env.sh`
Prepares staging environment variables file with all required production-grade configuration.

**Usage:**
```bash
./prepare-staging-env.sh
```

This will create or edit `.env.staging` with all required variables. You must fill in the actual values.

### `deploy-staging.sh`
Deploys the tagged release to staging environment using production environment variables.

**Usage:**
```bash
./deploy-staging.sh [version_tag]
```

**Example:**
```bash
./deploy-staging.sh v1.0.0
```

This script will:
1. Checkout the specified tag
2. Load environment variables from `.env.staging`
3. Build and start Docker containers
4. Run database migrations
5. Verify deployment health

### `run-verification-tests.sh`
Runs all verification tests and saves outputs to a log directory.

**Usage:**
```bash
./run-verification-tests.sh
```

This will:
1. Run all verification tests (tenant isolation, migrations, alerts, etc.)
2. Check feature flags, startup validation, metrics, database
3. Generate a summary report
4. Create an archive-ready log directory

### `canary-deployment.sh`
Manages canary deployment flags and monitoring.

**Usage:**
```bash
# Enable canary flags
./canary-deployment.sh [workspace_id] enable

# Monitor canary workspace
./canary-deployment.sh <workspace_id> monitor

# Disable canary flags
./canary-deployment.sh [workspace_id] disable
```

### `monitor-canary.sh`
Comprehensive canary monitoring script that runs periodic checks.

**Usage:**
```bash
./monitor-canary.sh <workspace_id> [duration_minutes]
```

**Example:**
```bash
# Monitor for 4 hours (default)
./monitor-canary.sh abc123-workspace-id

# Monitor for 2 hours
./monitor-canary.sh abc123-workspace-id 120
```

This will:
1. Run periodic cost and flag checks
2. Test kill switch response time
3. Generate monitoring logs and summary
4. Create success criteria checklist

## Deployment Workflow

### Phase 1: Tag and Deploy

```bash
# 1. Tag release
cd backend
./infra/scripts/tag-release.sh v1.0.0
git push origin v1.0.0

# 2. Prepare staging environment
./infra/scripts/prepare-staging-env.sh
# Edit .env.staging with actual values

# 3. Deploy to staging
./infra/scripts/deploy-staging.sh v1.0.0
```

### Phase 2: Verification

```bash
# Run all verification tests
./infra/scripts/run-verification-tests.sh

# Review logs
cd deployment-logs
ls -la
cat */VERIFICATION_SUMMARY.md

# Archive logs
tar -czf staging-verification-$(date +%Y%m%d).tar.gz */
```

### Phase 3: Canary Deployment

```bash
# 1. Enable canary flags
./infra/scripts/canary-deployment.sh <workspace_id> enable

# 2. Monitor canary workspace
./infra/scripts/monitor-canary.sh <workspace_id> 240  # 4 hours

# 3. If successful, flags are already enabled globally
#    Monitor all workspaces for 24 hours

# 4. If issues, disable immediately
./infra/scripts/canary-deployment.sh <workspace_id> disable
```

## Prerequisites

- Docker and Docker Compose installed
- Git repository access
- Staging server access
- Python environment (for running tests)
- pytest installed (`pip install pytest`)

## Environment Variables

All scripts expect `.env.staging` file with production-grade configuration. See `prepare-staging-env.sh` for required variables.

## Troubleshooting

### Deployment fails
- Check Docker logs: `docker logs byos_api`
- Verify environment variables are set correctly
- Ensure database is accessible
- Check startup validation logs

### Verification tests fail
- Review individual test log files
- Check if services are running: `docker ps`
- Verify database migrations completed: `docker exec byos_api alembic current`

### Canary monitoring issues
- Verify workspace ID is correct
- Check feature flags are enabled: `docker exec byos_api python -c "from core.autonomous.feature_flags import get_feature_flags; print(get_feature_flags().get_all_flags())"`
- Review monitoring logs in `deployment-logs/canary-monitoring-*/`

## Notes

- All 6 scripts use `set -euo pipefail` for strict error handling
- Scripts are designed to be idempotent (safe to re-run)
- Logs are timestamped and organized in `deployment-logs/` directory
- Canary flags are global but monitoring focuses on specific workspace
